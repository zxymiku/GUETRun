package com.local.runsimulator;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.*;

/** Java adaptation of the MIT Keep Data Simulator pipeline. See THIRD_PARTY_NOTICES. */
public final class ActivityGenerator {
    public static final class Config {
        public boolean cycling, treadmill, mapClosed;
        public double distanceM=5000, paceSec=330, speedKmh=25, lat=39.9042, lon=116.4074;
        public double radiusM=800, spacingM=10, gpsNoiseM=3, bearing=90;
        public double hrAvg=145, hrMax=190, hrRest=60, hrLag=30, hrNoise=3;
        public double gain=50, startElevation=50, warmupSeconds=0, warmupFactor=.8, splitRatio=.95;
        public double intervalFastSec=270, intervalSlowSec=390, fastSpeedKmh=30, slowSpeedKmh=18, fastSeconds=240, slowSeconds=120;
        public int hills=3, cadence=170, mapLaps; public long seed=42, startMillis=System.currentTimeMillis()/1000*1000;
        public String strategy="constant", route="circular", title="模拟跑步", timezone="Asia/Shanghai";
        public double[][] imported;
    }
    public static final class Point {
        public final double lat,lon,distance,elapsed,speed,elevation; public final int hr,cadence;
        Point(double lat,double lon,double distance,double elapsed,double speed,double elevation,int hr,int cadence){
            this.lat=lat;this.lon=lon;this.distance=distance;this.elapsed=elapsed;this.speed=speed;this.elevation=elevation;this.hr=hr;this.cadence=cadence;
        }
    }
    public static final class ActivityData {
        public final Config config; public final List<Point> points; public final double duration,distance,ascent,avgHr,avgCadence;
        ActivityData(Config c,List<Point> p){
            config=c;points=Collections.unmodifiableList(p); Point last=p.get(p.size()-1);duration=last.elapsed;distance=last.distance;
            double climb=0,hr=0,cad=0;for(int i=0;i<p.size();i++){hr+=p.get(i).hr;cad+=p.get(i).cadence;if(i>0)climb+=Math.max(0,p.get(i).elevation-p.get(i-1).elevation);}
            ascent=climb;avgHr=hr/p.size();avgCadence=cad/p.size();
        }
        public long endMillis(){return config.startMillis+Math.round(duration*1000);}
        public String endTimeText(){
            // FIT records have whole-second timestamps; display the same rounded finish second.
            return java.time.format.DateTimeFormatter.ofPattern("uuuu-MM-dd HH:mm:ss",Locale.ROOT)
                    .format(Instant.ofEpochMilli(config.startMillis+Math.round(duration)*1000).atZone(java.time.ZoneId.of(config.timezone)));
        }
        public String summary(){return String.format(Locale.ROOT,"%s · %s\n%.3f km  /  %s\n平均速度 %.2f km/h\n心率 %.0f bpm · %s %.0f\n爬升 %.1f m · %,d 个采样点\n开始 %s\n结束 %s\n随机种子 %d",
                config.cycling?"骑行":"跑步",config.treadmill?"跑步机":"户外",distance/1000,RunMath.duration(duration),distance/duration*3.6,avgHr,config.cycling?"踏频 rpm":"步频 spm",avgCadence,ascent,points.size(),Instant.ofEpochMilli(config.startMillis).atZone(java.time.ZoneId.of(config.timezone)),endTimeText(),config.seed);}
    }
    public static final double EARTH=6371000;
    private ActivityGenerator(){}
    private static boolean finite(double... nums){for(double n:nums)if(!Double.isFinite(n))return false;return true;}
    public static void validate(Config c){
        if(c.mapLaps<0||c.mapLaps>1000||(c.mapLaps>0&&(!"map".equals(c.route)||!c.mapClosed||c.treadmill)))throw new IllegalArgumentException("按圈数生成仅支持闭合地图路线，圈数范围 1–1000");
        if(!finite(c.distanceM,c.paceSec,c.speedKmh,c.lat,c.lon,c.radiusM,c.spacingM,c.gpsNoiseM,c.bearing,c.hrAvg,c.hrMax,c.hrRest,c.hrLag,c.hrNoise,c.gain,c.startElevation,c.warmupSeconds,c.warmupFactor,c.splitRatio,c.intervalFastSec,c.intervalSlowSec,c.fastSpeedKmh,c.slowSpeedKmh,c.fastSeconds,c.slowSeconds))throw new IllegalArgumentException("参数必须是有限数字");
        if(c.distanceM<10||c.distanceM>100000)throw new IllegalArgumentException("距离范围：10–100000 米");
        if(c.paceSec<=120||c.paceSec>=720||c.speedKmh<=5||c.speedKmh>=60)throw new IllegalArgumentException("配速须大于 2:00 且小于 12:00；骑行速度须大于 5 且小于 60 km/h");
        if(c.treadmill&&c.cycling)throw new IllegalArgumentException("跑步机模式仅支持跑步");
        if(Math.abs(c.lat)>80||Math.abs(c.lon)>180||c.radiusM<10||c.radiusM>20000||c.spacingM<1||c.spacingM>100||c.gpsNoiseM<0||c.gpsNoiseM>20)throw new IllegalArgumentException("请检查坐标、半径、间距或 GPS 噪声范围");
        if(c.distanceM/c.spacingM>20000)throw new IllegalArgumentException("采样点过多，请增加点间距（最多 20000 段）");
        if(c.hrRest<30||c.hrRest>=c.hrMax||c.hrAvg<c.hrRest||c.hrAvg>c.hrMax||c.hrMax>240||c.hrLag<=0||c.hrNoise<0||c.hrNoise>20)throw new IllegalArgumentException("心率须满足 30 ≤ 静息 ≤ 平均 ≤ 最大 ≤ 240；响应滞后须大于 0");
        if(c.cadence<(c.cycling?50:140)||c.cadence>(c.cycling?130:200))throw new IllegalArgumentException(c.cycling?"踏频范围 50–130 rpm":"步频范围 140–200 spm");
        if(c.hills<1||c.hills>20||c.gain<0||c.gain>5000||c.startElevation< -400||c.startElevation>8000)throw new IllegalArgumentException("请检查海拔或坡段数量");
        if(c.warmupSeconds<0||c.warmupSeconds>3600||c.warmupFactor<.2||c.warmupFactor>1||c.splitRatio<.5||c.splitRatio>1)throw new IllegalArgumentException("请检查热身或分段比例");
        if(c.intervalFastSec<=120||c.intervalFastSec>=720||c.intervalSlowSec<=120||c.intervalSlowSec>=720||c.fastSpeedKmh<=5||c.fastSpeedKmh>=60||c.slowSpeedKmh<=5||c.slowSpeedKmh>=60||c.fastSeconds<1||c.slowSeconds<1)throw new IllegalArgumentException("间歇参数超出范围");
        if(!Arrays.asList("constant","negative_split","positive_split","interval").contains(c.strategy))throw new IllegalArgumentException("未知配速策略");
        if(!Arrays.asList("circular","out_and_back","waypoint","gpx_import","coord_file","hand_drawn","map").contains(c.route))throw new IllegalArgumentException("未知路线类型");
        if(!c.treadmill&&!Arrays.asList("circular","out_and_back").contains(c.route)){
            if(c.imported==null||c.imported.length<2||c.imported.length>10000)throw new IllegalArgumentException("请提供 2–10000 个路线坐标点");
            for(double[] p:c.imported)if(p==null||p.length<2||!finite(p[0],p[1])||Math.abs(p[0])>80||Math.abs(p[1])>180)throw new IllegalArgumentException("路线包含无效坐标");
        }
        if(c.title==null||c.title.trim().isEmpty()||c.title.length()>80)throw new IllegalArgumentException("标题应为 1–80 个字符");
        java.time.ZoneId.of(c.timezone);
        int startYear=Instant.ofEpochMilli(c.startMillis).atZone(java.time.ZoneId.of(c.timezone)).getYear();
        if(startYear<1990||startYear>2099)throw new IllegalArgumentException("开始时间应在 1990–2099 年之间");
    }
    public static ActivityData simulate(Config c){
        if(c.mapLaps>0){if(!"map".equals(c.route)||c.treadmill)throw new IllegalArgumentException("按圈数生成仅支持闭合地图路线");c.distanceM=MapGeometry.lapDistance(c.imported,c.mapClosed,c.mapLaps);}
        validate(c); Random rng=new Random(c.seed);int segments=(int)Math.ceil(c.distanceM/c.spacingM);
        double[][] coords=c.treadmill?null:route(c,segments,rng);
        int n=c.treadmill?segments+1:coords.length;double[] d=new double[n],t=new double[n],s=new double[n];
        for(int i=1;i<n;i++){
            d[i]=c.treadmill?c.distanceM*i/segments:d[i-1]+haversine(coords[i-1][0],coords[i-1][1],coords[i][0],coords[i][1]);
            s[i]=speedAt(c,d[i]/c.distanceM,t[i-1]);t[i]=t[i-1]+(d[i]-d[i-1])/s[i];
            if(t[i]>86400)throw new IllegalArgumentException("生成时长超过 24 小时，请缩短距离");
        }
        s[0]=s[1]; double[] elevations=elevations(c,n,rng),hrs=new double[n];
        double min=Double.POSITIVE_INFINITY,max=0;for(double v:s){min=Math.min(min,v);max=Math.max(max,v);}
        double span=Math.min(c.hrAvg-c.hrRest,c.hrMax-c.hrAvg),alpha=1-Math.exp(-(t[n-1]/(n-1))/c.hrLag),mean=0;
        for(int i=0;i<n;i++){
            double effort=max>min?(s[i]-min)/(max-min):.5,target=c.hrAvg+(effort-.5)*2*span;
            hrs[i]=i==0?c.hrRest+(target-c.hrRest)*.3:alpha*target+(1-alpha)*hrs[i-1];mean+=hrs[i];
        }
        mean/=n;List<Point> points=new ArrayList<>(n);
        for(int i=0;i<n;i++){
            double effort=max>min?(s[i]-min)/(max-min):.5;
            int hr=(int)Math.round(clamp(hrs[i]*c.hrAvg/mean+rng.nextGaussian()*c.hrNoise,c.hrRest,c.hrMax));
            double cadSpan=c.cycling?15:10;
            int cadence=(int)Math.round(clamp(c.cadence-cadSpan/2+effort*cadSpan+rng.nextGaussian()*cadSpan*.1,c.cycling?50:140,c.cycling?130:200));
            points.add(new Point(c.treadmill?0:coords[i][0],c.treadmill?0:coords[i][1],d[i],t[i],s[i],elevations[i],hr,cadence));
        }
        return new ActivityData(c,points);
    }
    public static double speedAt(Config c,double fraction,double elapsed){
        double base=c.cycling?c.speedKmh/3.6:1000/c.paceSec,speed=base;
        if("negative_split".equals(c.strategy)||"positive_split".equals(c.strategy)){
            double ratio="negative_split".equals(c.strategy)?c.splitRatio:1/c.splitRatio;
            double first=base*2/(1+1/ratio);speed=fraction<.5?first:first/ratio;
        }else if("interval".equals(c.strategy)){
            double fast=c.cycling?c.fastSpeedKmh/3.6:1000/c.intervalFastSec,slow=c.cycling?c.slowSpeedKmh/3.6:1000/c.intervalSlowSec;
            speed=elapsed<c.warmupSeconds?slow:((elapsed-c.warmupSeconds)%(c.fastSeconds+c.slowSeconds)<c.fastSeconds?fast:slow);
        }
        return elapsed<c.warmupSeconds?speed*c.warmupFactor:speed;
    }
    private static double[][] route(Config c,int segments,Random rng){
        if("map".equals(c.route))return MapGeometry.sample(c.imported,c.mapClosed,c.distanceM,c.spacingM);
        List<double[]> base=new ArrayList<>();
        if("circular".equals(c.route)){
            int controls=Math.max(12,Math.min(360,(int)(c.distanceM/50)));
            for(int i=0;i<controls;i++)base.add(destination(c.lat,c.lon,c.radiusM*(1+(rng.nextDouble()-.5)*.3),360.0*i/controls+(rng.nextDouble()-.5)*6));base.add(base.get(0));
        }else if("out_and_back".equals(c.route)){
            base.add(new double[]{c.lat,c.lon});base.add(destination(c.lat,c.lon,c.distanceM/2,c.bearing));base.add(new double[]{c.lat,c.lon});
        }else{
            for(double[] p:c.imported)base.add(p.clone());
            if("waypoint".equals(c.route)&&haversine(base.get(0)[0],base.get(0)[1],base.get(base.size()-1)[0],base.get(base.size()-1)[1])>50)base.add(base.get(0).clone());
        }
        double[] cum=new double[base.size()];for(int i=1;i<cum.length;i++)cum[i]=cum[i-1]+haversine(base.get(i-1)[0],base.get(i-1)[1],base.get(i)[0],base.get(i)[1]);
        if(cum[cum.length-1]<1)throw new IllegalArgumentException("路线长度不足 1 米，请选择不同坐标");
        if(cum[cum.length-1]>2000000)throw new IllegalArgumentException("导入路线跨度过大，请使用同一地区的路线");
        double[][] coords=new double[segments+1][2];int j=1;
        for(int i=0;i<coords.length;i++){
            double pos=cum[cum.length-1]*i/segments;while(j<cum.length-1&&(cum[j]<pos||cum[j]==cum[j-1]))j++;
            double f=cum[j]==cum[j-1]?0:(pos-cum[j-1])/(cum[j]-cum[j-1]);
            coords[i][0]=base.get(j-1)[0]+(base.get(j)[0]-base.get(j-1)[0])*f;coords[i][1]=base.get(j-1)[1]+(base.get(j)[1]-base.get(j-1)[1])*f;
        }
        scale(coords,c.distanceM);
        if(c.gpsNoiseM>0){
            for(double[] p:coords){p[0]+=rng.nextGaussian()*c.gpsNoiseM/EARTH*180/Math.PI;p[1]+=rng.nextGaussian()*c.gpsNoiseM/(EARTH*Math.cos(Math.toRadians(p[0])))*180/Math.PI;}
            double[][] smoothed=new double[coords.length][2];
            for(int i=0;i<coords.length;i++)for(int k=0;k<2;k++){double sum=0;int count=0;for(int q=Math.max(0,i-2);q<=Math.min(coords.length-1,i+2);q++){sum+=coords[q][k];count++;}smoothed[i][k]=sum/count;}coords=smoothed;
        }
        scale(coords,c.distanceM);for(double[] p:coords)if(Math.abs(p[0])>80||Math.abs(p[1])>180)throw new IllegalArgumentException("路线越过坐标范围，请更换起点或缩短距离");return coords;
    }
    private static void scale(double[][] p,double target){
        double lat=0,lon=0;for(double[] q:p){lat+=q[0];lon+=q[1];}lat/=p.length;lon/=p.length;
        for(int k=0;k<8;k++){
            double total=0;for(int i=1;i<p.length;i++)total+=haversine(p[i-1][0],p[i-1][1],p[i][0],p[i][1]);
            if(total<.001)throw new IllegalArgumentException("路线坐标重合");if(Math.abs(total-target)<.001)return;
            double factor=target/total;for(double[] q:p){q[0]=lat+(q[0]-lat)*factor;q[1]=lon+(q[1]-lon)*factor;}
        }
    }
    private static double[] elevations(Config c,int n,Random rng){
        double[] e=new double[n];if(c.treadmill||c.gain==0){Arrays.fill(e,c.startElevation);return e;}
        for(int i=0;i<n;i++){double phase=(i/(double)(n-1)*c.hills)%1;e[i]=(phase<.5?phase*2:(1-phase)*2)*c.gain/c.hills+rng.nextGaussian()*.5;}
        double ascent=0;for(int i=1;i<n;i++)ascent+=Math.max(0,e[i]-e[i-1]);double first=e[0];for(int i=0;i<n;i++)e[i]=c.startElevation+(e[i]-first)*c.gain/Math.max(.0001,ascent);return e;
    }
    public static double haversine(double lat,double lon,double a,double b){double x=Math.sin(Math.toRadians(a-lat)/2),y=Math.sin(Math.toRadians(b-lon)/2);return EARTH*2*Math.asin(Math.sqrt(clamp(x*x+Math.cos(Math.toRadians(lat))*Math.cos(Math.toRadians(a))*y*y,0,1)));}
    private static double[] destination(double lat,double lon,double distance,double bearing){
        double la=Math.toRadians(lat),lo=Math.toRadians(lon),b=Math.toRadians(bearing),d=distance/EARTH,l=Math.asin(Math.sin(la)*Math.cos(d)+Math.cos(la)*Math.sin(d)*Math.cos(b));
        return new double[]{Math.toDegrees(l),Math.toDegrees(lo+Math.atan2(Math.sin(b)*Math.sin(d)*Math.cos(la),Math.cos(d)-Math.sin(la)*Math.sin(l)))};
    }
    public static void writeGpx(ActivityData data,OutputStream out)throws IOException{
        if(data.config.treadmill)throw new IllegalArgumentException("无 GPS 的跑步机活动请保存为 FIT");Writer w=new BufferedWriter(new OutputStreamWriter(out,StandardCharsets.UTF_8));
        w.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<gpx version=\"1.1\" creator=\"RunLab Android Simulator\" xmlns=\"http://www.topografix.com/GPX/1/1\" xmlns:gpxtpx=\"http://www.garmin.com/xmlschemas/TrackPointExtension/v1\"><metadata><desc>Simulated test activity</desc><time>"+Instant.ofEpochMilli(data.config.startMillis)+"</time></metadata><trk><name>"+esc(data.config.title)+"</name><type>"+(data.config.cycling?"cycling":"running")+"</type><trkseg>\n");
        for(Point p:data.points)w.write(String.format(Locale.ROOT,"<trkpt lat=\"%.8f\" lon=\"%.8f\"><ele>%.3f</ele><time>%s</time><extensions><gpxtpx:TrackPointExtension><gpxtpx:hr>%d</gpxtpx:hr><gpxtpx:cad>%d</gpxtpx:cad></gpxtpx:TrackPointExtension></extensions></trkpt>\n",p.lat,p.lon,p.elevation,Instant.ofEpochMilli(data.config.startMillis+Math.round(p.elapsed*1000)),p.hr,p.cadence));w.write("</trkseg></trk></gpx>");w.flush();
    }
    public static String filename(String title,String format){String safe=title.replaceAll("[^\\p{L}\\p{N}_-]","_");return (safe.isEmpty()?"Activity":safe)+"."+format;}
    private static String esc(String x){return x.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\"","&quot;").replaceAll("[\\x00-\\x08\\x0B\\x0C\\x0E-\\x1F]","");}
    private static double clamp(double x,double min,double max){return Math.max(min,Math.min(max,x));}
}
