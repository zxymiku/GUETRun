package com.local.runsimulator;

import android.app.*;
import android.content.*;
import android.location.*;
import android.os.*;
import java.util.ArrayList;

public class RunService extends Service {
    public static final String STOP = "com.local.runsimulator.STOP";
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final ArrayList<String> installed = new ArrayList<>();
    private LocationManager manager;
    private PowerManager.WakeLock wake;
    private double lat, lon, meters, pace, lap;
    private long began;
    private boolean active;
    private android.content.SharedPreferences state;
    private String channels="";
    private final LocationListener observer=new LocationListener(){
        @Override public void onLocationChanged(Location location){
            state.edit().putString("received_"+location.getProvider(),String.format(java.util.Locale.ROOT,
                    "%.6f, %.6f · 模拟=%s",location.getLatitude(),location.getLongitude(),location.isFromMockProvider()))
                    .putLong("received_at_"+location.getProvider(),SystemClock.elapsedRealtime()).apply();
        }
        @Override public void onStatusChanged(String p,int s,Bundle extras){}
        @Override public void onProviderEnabled(String p){}
        @Override public void onProviderDisabled(String p){}
    };

    @Override public void onCreate() {
        super.onCreate();
        manager = (LocationManager)getSystemService(LOCATION_SERVICE);
        state = getSharedPreferences("run", MODE_PRIVATE);
        NotificationChannel channel = new NotificationChannel("simulation", "跑步模拟", NotificationManager.IMPORTANCE_LOW);
        getSystemService(NotificationManager.class).createNotificationChannel(channel);
    }
    @Override public int onStartCommand(Intent intent, int flags, int id) {
        if (intent == null || STOP.equals(intent.getAction())) { stopSelf(); return START_NOT_STICKY; }
        if (active) return START_NOT_STICKY;
        try {
            startForeground(1, notification("正在准备模拟定位"));
            lat=intent.getDoubleExtra("lat",Double.NaN); lon=intent.getDoubleExtra("lon",Double.NaN);
            meters=intent.getDoubleExtra("meters",0); pace=intent.getDoubleExtra("pace",0); lap=intent.getDoubleExtra("lap",0);
            if (!Double.isFinite(lat) || !Double.isFinite(lon) || Math.abs(lat)>80 || Math.abs(lon)>180
                    || !Double.isFinite(meters) || meters<=0 || meters>100000
                    || !Double.isFinite(pace) || pace<120 || pace>3600
                    || !Double.isFinite(lap) || lap<100 || lap>10000
                    || meters/1000*pace>86400) throw new IllegalArgumentException("模拟参数超出范围");
            state.edit().remove("received_gps").remove("received_network").remove("received_fused")
                    .remove("received_at_gps").remove("received_at_network").remove("received_at_fused").putLong("sent",0).apply();
            java.util.List<String> available=manager.getAllProviders();
            for (String provider : new String[]{LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER,"fused"}) {
                if("fused".equals(provider) && !available.contains(provider)){
                    channels+="fused：系统未提供\n";continue;
                }
                try{
                    manager.addTestProvider(provider, false,false,false,false,true,true,true, android.location.Criteria.POWER_LOW, android.location.Criteria.ACCURACY_FINE);
                    installed.add(provider);
                    manager.setTestProviderEnabled(provider,true);
                    channels+=provider+"：已启用\n";
                    try{manager.requestLocationUpdates(provider,1000,0,observer,Looper.getMainLooper());}
                    catch(Exception readError){channels+=provider+"：回读订阅失败 "+readError.getClass().getSimpleName()+"\n";}
                }catch(Exception providerError){
                    channels+=provider+"："+providerError.getClass().getSimpleName()+" "+providerError.getMessage()+"\n";
                    if(LocationManager.GPS_PROVIDER.equals(provider))throw providerError;
                }
            }
            state.edit().putString("channels",channels).apply();
            began=SystemClock.elapsedRealtime(); active=true;
            wake=((PowerManager)getSystemService(POWER_SERVICE)).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"runsimulator:run");
            wake.acquire((long)(meters/1000*pace*1000)+60000);
            state.edit().putBoolean("active",true).putString("message","模拟进行中").putFloat("distance",0).putLong("elapsed",0).apply();
            handler.post(tick);
        } catch (Exception e) { fail(e); }
        return START_NOT_STICKY;
    }
    private final Runnable tick = new Runnable() { public void run() {
        if (!active) return;
        try {
            double elapsed=Math.min((SystemClock.elapsedRealtime()-began)/1000.0, meters/1000*pace);
            double distance=Math.min(meters,elapsed*1000/pace);
            double[] pos=RunMath.point(lat,lon,lap,distance);
            double[] next=RunMath.point(lat,lon,lap,distance+1);
            float[] bearing=new float[3]; Location.distanceBetween(pos[0],pos[1],next[0],next[1],bearing);
            for (String provider : installed) {
                Location location=new Location(provider);
                location.setLatitude(pos[0]); location.setLongitude(pos[1]); location.setAltitude(0);
                location.setAccuracy(3); location.setSpeed(distance>=meters?0:(float)(1000/pace)); location.setBearing(bearing[1]);
                location.setSpeedAccuracyMetersPerSecond(0.1f); location.setBearingAccuracyDegrees(1);
                location.setVerticalAccuracyMeters(3);
                location.setTime(System.currentTimeMillis()); location.setElapsedRealtimeNanos(SystemClock.elapsedRealtimeNanos());
                manager.setTestProviderLocation(provider,location);
            }
            state.edit().putFloat("distance",(float)distance).putLong("elapsed",(long)elapsed)
                    .putLong("sent",state.getLong("sent",0)+1).apply();
            getSystemService(NotificationManager.class).notify(1,notification(String.format(java.util.Locale.ROOT,"%.2f km · %s",distance/1000,RunMath.duration(elapsed))));
            if (distance>=meters) { state.edit().putString("message","模拟完成；请在 Keep 中检查并手动结束运动").apply(); stopSelf(); }
            else handler.postDelayed(this,1000);
        } catch(Exception e) { fail(e); }
    }};
    private Notification notification(String message) {
        PendingIntent open=PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class),PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        PendingIntent stop=PendingIntent.getService(this,1,new Intent(this,RunService.class).setAction(STOP),PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        return new Notification.Builder(this,"simulation").setContentTitle("跑步模拟器 · 模拟数据")
                .setContentText(message).setSmallIcon(android.R.drawable.ic_media_play).setContentIntent(open).setOngoing(true)
                .addAction(new Notification.Action.Builder(null,"停止模拟",stop).build()).build();
    }
    private void fail(Exception e) {
        state.edit().putString("channels",channels).putString("message","无法模拟："+e.getClass().getSimpleName()+" · "+e.getMessage()+"。请检查精确位置权限、系统定位开关和模拟位置应用设置。" ).apply();
        stopSelf();
    }
    @Override public void onDestroy() {
        active=false; handler.removeCallbacksAndMessages(null);
        try{manager.removeUpdates(observer);}catch(Exception ignored){}
        for(String provider:installed) try { manager.removeTestProvider(provider); } catch(Exception ignored) {}
        installed.clear(); if(wake!=null && wake.isHeld()) wake.release();
        state.edit().putBoolean("active",false).apply(); stopForeground(STOP_FOREGROUND_REMOVE);
        super.onDestroy();
    }
    @Override public IBinder onBind(Intent intent) { return null; }
}
