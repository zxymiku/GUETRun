package com.local.runsimulator;

import android.content.Context;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;

final class MapRouteStore {
    static final class Route {
        double[][] points;
        boolean closed;
        String name;
        int laps;
        String mode="line";
        JSONObject editor;
    }
    static Route read(Context c)throws Exception {
        File file=new File(c.getFilesDir(),"map-route.json");if(!file.isFile())return null;
        try(InputStream in=new FileInputStream(file)){
            ByteArrayOutputStream bytes=new ByteArrayOutputStream();byte[] b=new byte[8192];int n;
            while((n=in.read(b))!=-1){bytes.write(b,0,n);if(bytes.size()>2000000)throw new IOException("路线文件过大");}
            JSONObject json=new JSONObject(bytes.toString("UTF-8"));Route route=new Route();
            route.closed=json.getBoolean("closed");route.name=json.optString("name","地图路线");
            route.laps=json.optInt("laps",0);route.mode=json.optString("mode","line");route.editor=json.optJSONObject("editor");
            JSONArray points=json.getJSONArray("points");if(points.length()<2||points.length()>10000)throw new IOException("路线点数无效");
            route.points=new double[points.length()][2];for(int i=0;i<points.length();i++){
                JSONArray p=points.getJSONArray(i);route.points[i][0]=p.getDouble(0);route.points[i][1]=p.getDouble(1);
            }
            MapGeometry.sample(route.points,route.closed,10,10);if(route.laps!=0)MapGeometry.lapDistance(route.points,route.closed,route.laps);return route;
        }
    }
    static void write(Context c,Route route)throws Exception {
        MapGeometry.sample(route.points,route.closed,10,10);
        if(route.laps!=0)MapGeometry.lapDistance(route.points,route.closed,route.laps);
        JSONObject json=new JSONObject();json.put("closed",route.closed);json.put("name",route.name);
        json.put("laps",route.laps);json.put("mode",route.mode);if(route.editor!=null)json.put("editor",route.editor);
        JSONArray pts=new JSONArray();for(double[] p:route.points)pts.put(new JSONArray().put(p[0]).put(p[1]));json.put("points",pts);
        android.util.AtomicFile file=new android.util.AtomicFile(new File(c.getFilesDir(),"map-route.json"));
        FileOutputStream out=null;try{out=file.startWrite();out.write(json.toString().getBytes(StandardCharsets.UTF_8));file.finishWrite(out);}
        catch(Exception e){if(out!=null)file.failWrite(out);throw e;}
    }
    static double length(Route r){return MapGeometry.length(r.points,r.closed);}
}
