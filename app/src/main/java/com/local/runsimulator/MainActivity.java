package com.local.runsimulator;

import android.Manifest;
import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.graphics.*;
import android.os.*;
import android.provider.Settings;
import android.view.*;
import android.widget.*;
import java.util.Locale;

public class MainActivity extends Activity {
    private EditText distance, pace, minutes, latitude, longitude, lap;
    private TextView result, status;
    private RouteView route;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private android.content.SharedPreferences prefs;
    private final Runnable refresh=new Runnable(){ public void run(){
        android.content.SharedPreferences state=getSharedPreferences("run",MODE_PRIVATE);
        status.setText((state.getBoolean("active",false)?"● 正在模拟":"○ 已停止")+"\n"+
            String.format(Locale.ROOT,"%.2f km  /  %s\n",state.getFloat("distance",0)/1000,RunMath.duration(state.getLong("elapsed",0)))+
            state.getString("message","准备好参数后开始；定位数据会被标记为模拟。")+"\n\n"+diagnostics());
        handler.postDelayed(this,1000);
    }};
    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved); prefs=getSharedPreferences("inputs",MODE_PRIVATE);
        boolean running=false;
        for(ActivityManager.RunningServiceInfo service:((ActivityManager)getSystemService(ACTIVITY_SERVICE)).getRunningServices(Integer.MAX_VALUE))
            if(RunService.class.getName().equals(service.service.getClassName())) running=true;
        if(!running)getSharedPreferences("run",MODE_PRIVATE).edit().putBoolean("active",false).apply();
        ScrollView scroll=new ScrollView(this); LinearLayout body=new LinearLayout(this);
        body.setOrientation(LinearLayout.VERTICAL); body.setPadding(28,40,28,32); body.setBackgroundColor(Color.rgb(246,248,250)); scroll.addView(body); setContentView(scroll);
        label(body,"RUN / LAB · 1.1",15,Color.rgb(0,119,101)); label(body,"跑步模拟器",30,Color.rgb(20,35,44));
        label(body,"距离 · 配速 · 时间，自由换算",16,Color.DKGRAY);
        label(body,"通过 Android 原生模拟定位提供测试轨迹。Keep 是否接受由其版本与校验决定，本应用不能直接写入 Keep 记录。",14,Color.DKGRAY);
        distance=input(body,"距离（公里，最多 100）","distance","5",false);
        pace=input(body,"配速（分:秒 / 公里，例如 6:00）","pace","6:00",true);
        minutes=input(body,"时间（分钟，最多 1440）","minutes","30",false);
        LinearLayout calc=new LinearLayout(this); body.addView(calc);
        button(calc,"计算时间",v->calculate(0)); button(calc,"计算距离",v->calculate(1)); button(calc,"计算配速",v->calculate(2));
        result=label(body,"",18,Color.rgb(0,119,101)); calculate(0);
        label(body,"模拟路线 · 环形",22,Color.rgb(20,35,44));
        latitude=input(body,"起点纬度（WGS84，-80 至 80）","latitude","39.9042",true);
        longitude=input(body,"起点经度（WGS84，-180 至 180）","longitude","116.4074",true);
        lap=input(body,"每圈距离（米，100–10000）","lap","400",false);
        label(body,"默认坐标仅为示例，请改为测试地点。轨迹从起点向北出发并向东绕圈；按实际时间运行。",13,Color.DKGRAY);
        route=new RouteView(); body.addView(route,new LinearLayout.LayoutParams(-1,240));
        button(body,"预览路线",v->{try{validateRoute(); route.invalidate();}catch(Exception e){error(e);}});
        button(body,"① 授权位置与通知",v->requestPermissions(Build.VERSION.SDK_INT>=33?new String[]{Manifest.permission.ACCESS_FINE_LOCATION,Manifest.permission.ACCESS_COARSE_LOCATION,Manifest.permission.POST_NOTIFICATIONS}:new String[]{Manifest.permission.ACCESS_FINE_LOCATION,Manifest.permission.ACCESS_COARSE_LOCATION},10));
        button(body,"② 打开开发者选项",v->{try{startActivity(new Intent(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS));}catch(Exception e){startActivity(new Intent(Settings.ACTION_SETTINGS));}});
        label(body,"先在系统设置中启用开发者选项，再将“选择模拟位置信息应用”设为“跑步模拟器”。开始后手动打开 Keep 的户外跑步，等待其定位并开始运动。",14,Color.DKGRAY);
        button(body,"③ 开始模拟",v->startRun());
        button(body,"停止模拟并恢复定位",v->{stopService(new Intent(this,RunService.class)); getSharedPreferences("run",MODE_PRIVATE).edit().putString("message","模拟已手动停止").apply();});
        status=label(body,"",16,Color.rgb(20,35,44));
        button(body,"复制定位诊断（含坐标）",v->{
            ((android.content.ClipboardManager)getSystemService(CLIPBOARD_SERVICE)).setPrimaryClip(ClipData.newPlainText("定位诊断",status.getText()));
            Toast.makeText(this,"诊断已复制",Toast.LENGTH_SHORT).show();
        });
        label(body,"模拟会影响本机其他使用位置的应用；停止后移除测试定位提供者。系统会保留模拟标记。请仅用于自测，避免提交为真实运动或活动成绩。",13,Color.DKGRAY);
    }
    private String diagnostics(){
        android.content.SharedPreferences s=getSharedPreferences("run",MODE_PRIVATE);
        StringBuilder text=new StringBuilder("定位诊断 · ").append(Build.MANUFACTURER).append(" ").append(Build.MODEL)
                .append(" / Android ").append(Build.VERSION.RELEASE).append("\n成功发送轮次：").append(s.getLong("sent",0)).append("\n")
                .append(s.getString("channels","尚未启动"));
        for(String p:new String[]{"gps","network","fused"}){
            long at=s.getLong("received_at_"+p,0);
            text.append("\n").append(p).append(" 回读：").append(s.getString("received_"+p,"未收到"));
            if(at>0)text.append("（").append(Math.max(0,(SystemClock.elapsedRealtime()-at)/1000)).append(" 秒前）");
        }
        return text.append("\n回读表示本应用收到了系统位置，不代表 Keep 已读取。系统 fused 与 Google/厂商融合定位接口可能不同。\n如果 Keep 仍为 0，请确认户外模式、精确位置权限、已开始且未暂停，并提供本页诊断。").toString();
    }
    private TextView label(LinearLayout parent,String text,int size,int color){TextView v=new TextView(this);v.setText(text);v.setTextSize(size);v.setTextColor(color);v.setPadding(0,8,0,12);parent.addView(v);return v;}
    private EditText input(LinearLayout parent,String title,String key,String initial,boolean text){
        label(parent,title,14,Color.DKGRAY);EditText e=new EditText(this); e.setSingleLine(true);e.setText(prefs.getString(key,initial));e.setTag(key);
        e.setInputType(text?android.text.InputType.TYPE_CLASS_TEXT:android.text.InputType.TYPE_CLASS_NUMBER|android.text.InputType.TYPE_NUMBER_FLAG_DECIMAL);
        parent.addView(e,new LinearLayout.LayoutParams(-1,-2));return e;
    }
    private void button(LinearLayout parent,String title,View.OnClickListener listener){Button b=new Button(this);b.setText(title);b.setAllCaps(false);b.setOnClickListener(listener);parent.addView(b,new LinearLayout.LayoutParams(parent.getOrientation()==LinearLayout.HORIZONTAL?0:-1,-2,parent.getOrientation()==LinearLayout.HORIZONTAL?1:0));}
    private void calculate(int mode){try{
        double d,p,t;
        if(mode==0){d=RunMath.positive(distance.getText().toString());p=RunMath.pace(pace.getText().toString());t=d*p;minutes.setText(String.format(Locale.ROOT,"%.4f",t/60));}
        else if(mode==1){p=RunMath.pace(pace.getText().toString());t=RunMath.positive(minutes.getText().toString())*60;d=t/p;distance.setText(String.format(Locale.ROOT,"%.4f",d));}
        else{d=RunMath.positive(distance.getText().toString());t=RunMath.positive(minutes.getText().toString())*60;p=t/d;long s=Math.round(p);pace.setText(String.format(Locale.ROOT,"%d:%02d",s/60,s%60));}
        result.setText(String.format(Locale.ROOT,"%.3f km  ·  %s  ·  %.2f km/h",d,RunMath.duration(t),3600/p));save();
    }catch(Exception e){error(e);}}
    private void save(){android.content.SharedPreferences.Editor ed=prefs.edit();for(EditText e:new EditText[]{distance,pace,minutes,latitude,longitude,lap})if(e!=null)ed.putString((String)e.getTag(),e.getText().toString());ed.apply();}
    private double[] validateRoute(){double a=Double.parseDouble(latitude.getText().toString()),o=Double.parseDouble(longitude.getText().toString()),l=RunMath.positive(lap.getText().toString());if(!Double.isFinite(a)||!Double.isFinite(o)||Math.abs(a)>80||Math.abs(o)>180||l<100||l>10000)throw new IllegalArgumentException("请检查经纬度或每圈距离范围");return new double[]{a,o,l};}
    private void startRun(){try{
        if(checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)!=PackageManager.PERMISSION_GRANTED)throw new IllegalArgumentException("请先授予精确位置权限");
        if(getSharedPreferences("run",MODE_PRIVATE).getBoolean("active",false))throw new IllegalArgumentException("模拟已在运行，请先停止再修改参数");
        double[] r=validateRoute(); double d=RunMath.positive(distance.getText().toString()),p=RunMath.pace(pace.getText().toString());
        if(d>100||p<120||p>3600||d*p>86400)throw new IllegalArgumentException("距离最多 100 公里，配速 2:00–60:00，总时间最多 24 小时");
        save();calculate(0);
        startForegroundService(new Intent(this,RunService.class).putExtra("lat",r[0]).putExtra("lon",r[1]).putExtra("lap",r[2]).putExtra("meters",d*1000).putExtra("pace",p));
    }catch(Exception e){error(e);}}
    private void error(Exception e){new AlertDialog.Builder(this).setTitle("请检查设置").setMessage(e instanceof NumberFormatException?"请输入有效数字；经纬度使用小数格式。":e.getMessage()).setPositiveButton("知道了",null).show();}
    @Override protected void onResume(){super.onResume();handler.post(refresh);}
    @Override protected void onPause(){handler.removeCallbacks(refresh);save();super.onPause();}
    private class RouteView extends View{
        private final Paint paint=new Paint(3);
        RouteView(){super(MainActivity.this);}
        @Override protected void onDraw(Canvas c){super.onDraw(c);float radius=Math.min(getWidth()/3f,getHeight()/2f-32),cx=getWidth()/2f,cy=getHeight()/2f;
            paint.setColor(Color.rgb(216,233,229));paint.setStyle(Paint.Style.FILL);c.drawCircle(cx,cy,radius,paint);
            paint.setColor(Color.rgb(0,145,118));paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(5);c.drawCircle(cx,cy,radius,paint);
            paint.setStyle(Paint.Style.FILL);c.drawCircle(cx-radius,cy,8,paint);paint.setTextSize(27);c.drawText("起点 → 向北",cx-radius+12,cy,paint);
        }
    }
}
