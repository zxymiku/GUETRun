package com.local.runsimulator;

import java.util.ArrayList;
import java.util.List;

/** Map display uses GCJ-02; all stored/exported tracks use WGS84. */
public final class MapGeometry {
    private static final double A=6378245.0, EE=0.00669342162296594323;
    private MapGeometry() {}
    private static boolean outside(double lat,double lon) {
        return lon<72.004||lon>137.8347||lat<0.8293||lat>55.8271;
    }
    public static double[] toGcj(double lat,double lon) {
        if(outside(lat,lon))return new double[]{lat,lon};
        double x=lon-105,y=lat-35;
        double dy=-100+2*x+3*y+.2*y*y+.1*x*y+.2*Math.sqrt(Math.abs(x));
        dy+=(20*Math.sin(6*x*Math.PI)+20*Math.sin(2*x*Math.PI))*2/3;
        dy+=(20*Math.sin(y*Math.PI)+40*Math.sin(y/3*Math.PI))*2/3;
        dy+=(160*Math.sin(y/12*Math.PI)+320*Math.sin(y*Math.PI/30))*2/3;
        double dx=300+x+2*y+.1*x*x+.1*x*y+.1*Math.sqrt(Math.abs(x));
        dx+=(20*Math.sin(6*x*Math.PI)+20*Math.sin(2*x*Math.PI))*2/3;
        dx+=(20*Math.sin(x*Math.PI)+40*Math.sin(x/3*Math.PI))*2/3;
        dx+=(150*Math.sin(x/12*Math.PI)+300*Math.sin(x/30*Math.PI))*2/3;
        double rad=Math.toRadians(lat),magic=1-EE*Math.sin(rad)*Math.sin(rad),root=Math.sqrt(magic);
        return new double[]{lat+dy*180/((A*(1-EE))/(magic*root)*Math.PI),
                lon+dx*180/(A/root*Math.cos(rad)*Math.PI)};
    }
    public static double[] toWgs(double lat,double lon) {
        if(outside(lat,lon))return new double[]{lat,lon};
        double a=lat,b=lon;
        for(int i=0;i<12;i++){
            double[] q=toGcj(a,b);double da=q[0]-lat,db=q[1]-lon;
            a-=da;b-=db;if(Math.max(Math.abs(da),Math.abs(db))<1e-10)break;
        }
        return new double[]{a,b};
    }
    /** Follow the path without scaling it. Closed paths repeat; open paths return along themselves. */
    public static double[][] sample(double[][] input,boolean closed,double target,double spacing) {
        if(!Double.isFinite(target)||target<10||target>100000||!Double.isFinite(spacing)||spacing<1||spacing>100)
            throw new IllegalArgumentException("地图路线距离或采样间距无效");
        if(input==null||input.length<2||input.length>10000)throw new IllegalArgumentException("请在地图上绘制路线");
        List<double[]> path=new ArrayList<>();
        for(double[] p:input){
            if(p==null||p.length<2||!Double.isFinite(p[0])||!Double.isFinite(p[1])||Math.abs(p[0])>80||Math.abs(p[1])>180)
                throw new IllegalArgumentException("地图包含无效坐标");
            if(path.isEmpty()||distance(path.get(path.size()-1),p)>.01)path.add(p.clone());
        }
        if(path.size()<2)throw new IllegalArgumentException("路线坐标重合，请重新绘制");
        double oneWay=0;for(int i=1;i<path.size();i++)oneWay+=distance(path.get(i-1),path.get(i));
        if(closed&&distance(path.get(path.size()-1),path.get(0))>.01)path.add(path.get(0).clone());
        else if(!closed){for(int i=path.size()-2;i>=0;i--)path.add(path.get(i).clone());}
        if(oneWay<10||oneWay>2000000)throw new IllegalArgumentException("地图路线长度须在 10 米至 2000 公里之间");
        List<double[]> out=new ArrayList<>();out.add(path.get(0).clone());double traveled=0;int edge=1;
        while(target-traveled>1e-6){
            double[] from=out.get(out.size()-1),end=path.get(edge);
            double left=distance(from,end);
            if(left<1e-6){edge=edge==path.size()-1?1:edge+1;continue;}
            double step=Math.min(Math.min(spacing,left),target-traveled);
            double[] next=step>=left-1e-7?end.clone():interpolate(from,end,step/left);
            out.add(next);traveled+=step;
            if(out.size()>20001)throw new IllegalArgumentException("地图路线采样点超过 20000 段，请增大间距或简化路线");
            if(step>=left-1e-7)edge=edge==path.size()-1?1:edge+1;
        }
        return out.toArray(new double[0][]);
    }
    public static double distance(double[] a,double[] b){return ActivityGenerator.haversine(a[0],a[1],b[0],b[1]);}
    public static double length(double[][] points,boolean closed){
        if(points==null||points.length<2)throw new IllegalArgumentException("路线至少需要两个坐标");
        double total=0;for(int i=1;i<points.length;i++)total+=distance(points[i-1],points[i]);
        if(closed)total+=distance(points[points.length-1],points[0]);return total;
    }
    public static double lapDistance(double[][] points,boolean closed,int laps){
        if(!closed||laps<1||laps>1000)throw new IllegalArgumentException("按圈数生成须使用闭合路线，圈数范围 1–1000");
        double total=length(points,true)*laps;
        if(!Double.isFinite(total)||total<10||total>100000)throw new IllegalArgumentException("圈数对应的总里程须在 10 米至 100 公里之间");
        return total;
    }
    private static double[] interpolate(double[] a,double[] b,double f) {
        double la=Math.toRadians(a[0]),lo=Math.toRadians(a[1]),lb=Math.toRadians(b[0]),lob=Math.toRadians(b[1]);
        double angle=distance(a,b)/ActivityGenerator.EARTH;
        double x=Math.sin((1-f)*angle)/Math.sin(angle),y=Math.sin(f*angle)/Math.sin(angle);
        double vx=x*Math.cos(la)*Math.cos(lo)+y*Math.cos(lb)*Math.cos(lob);
        double vy=x*Math.cos(la)*Math.sin(lo)+y*Math.cos(lb)*Math.sin(lob),vz=x*Math.sin(la)+y*Math.sin(lb);
        return new double[]{Math.toDegrees(Math.atan2(vz,Math.hypot(vx,vy))),Math.toDegrees(Math.atan2(vy,vx))};
    }
}
