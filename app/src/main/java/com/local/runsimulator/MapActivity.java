package com.local.runsimulator;

import android.app.*;
import android.content.*;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.view.View;
import android.webkit.*;
import android.widget.*;
import org.json.*;
import java.io.*;

/** Official AMap JS API, displayed over a bundled local editing page. */
public final class MapActivity extends Activity {
    private WebView web;
    private TextView status;
    private boolean trustedPage;
    private final String origin="https://runlab.local/";
    @Override public void onCreate(Bundle state){
        super.onCreate(state);LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(12,12,12,0);root.setBackgroundColor(Color.rgb(246,248,250));setContentView(root);
        if(android.os.Build.VERSION.SDK_INT>=30)root.setOnApplyWindowInsetsListener((view,insets)->{
            android.graphics.Insets edges=insets.getInsets(android.view.WindowInsets.Type.systemBars()|android.view.WindowInsets.Type.displayCutout());
            view.setPadding(12+edges.left,12+edges.top,12+edges.right,edges.bottom);return insets;
        });
        LinearLayout bar=new LinearLayout(this);root.addView(bar);
        button(bar,"返回",v->finish());button(bar,"地图密钥 / 申请说明",v->settings());button(bar,"重载",v->load());
        status=new TextView(this);status.setPadding(12,8,12,8);status.setTextSize(13);root.addView(status);
        web=new WebView(this);root.addView(web,new LinearLayout.LayoutParams(-1,0,1));
        WebSettings s=web.getSettings();s.setJavaScriptEnabled(true);s.setDomStorageEnabled(true);
        s.setAllowFileAccess(false);s.setAllowContentAccess(false);s.setGeolocationEnabled(false);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);s.setSupportMultipleWindows(false);
        web.setWebViewClient(new WebViewClient(){
            @Override public boolean shouldOverrideUrlLoading(WebView v,WebResourceRequest r){return true;}
            @Override public void onPageFinished(WebView v,String url){
                if(trustedPage&&url.startsWith(origin))bootstrap();
            }
            @Override public void onReceivedError(WebView v,WebResourceRequest r,WebResourceError e){
                if(r.isForMainFrame())status.setText("地图加载失败，请检查网络后重载");
            }
        });
        web.addJavascriptInterface(new Bridge(),"RouteApp");load();
        if(prefs().getString("key","").isEmpty())settings();
    }
    private android.content.SharedPreferences prefs(){return getSharedPreferences("amap",MODE_PRIVATE);}
    private void button(LinearLayout p,String label,View.OnClickListener action){Button b=new Button(this);b.setText(label);b.setTextSize(12);b.setAllCaps(false);b.setOnClickListener(action);p.addView(b,new LinearLayout.LayoutParams(0,-2,1));}
    private void load(){
        try(InputStream in=getAssets().open("route-map.html")){
            ByteArrayOutputStream bytes=new ByteArrayOutputStream();byte[] buf=new byte[8192];int n;while((n=in.read(buf))!=-1)bytes.write(buf,0,n);
            trustedPage=true;status.setText("高德地图 · 需要联网；所画路线仅保存到本机");
            web.loadDataWithBaseURL(origin,bytes.toString("UTF-8"),"text/html","UTF-8",null);
        }catch(Exception e){status.setText("地图页面无法打开："+e.getMessage());}
    }
    private void bootstrap(){
        try{
            JSONObject state=new JSONObject();state.put("key",prefs().getString("key",""));state.put("security",prefs().getString("security",""));
            double lat=getIntent().getDoubleExtra("lat",39.9042),lon=getIntent().getDoubleExtra("lon",116.4074);
            double[] center=MapGeometry.toGcj(lat,lon);state.put("center",new JSONArray().put(center[0]).put(center[1]));
            state.put("radius",getIntent().getDoubleExtra("radius",100));
            try{
                MapRouteStore.Route route=MapRouteStore.read(this);
                if(route!=null){JSONArray points=new JSONArray();for(double[] p:route.points){double[] q=MapGeometry.toGcj(p[0],p[1]);points.put(new JSONArray().put(q[0]).put(q[1]));}
                    state.put("points",points);state.put("closed",route.closed);state.put("laps",route.laps);state.put("mode",route.mode);
                    if(route.editor!=null)state.put("editor",route.editor);}
            }catch(Exception ignored){status.setText("旧路线无法读取，请重新绘制");}
            web.evaluateJavascript("window.boot("+state.toString()+")",null);
        }catch(Exception e){status.setText("地图初始化失败："+e.getMessage());}
    }
    private void settings(){
        ScrollView scroll=new ScrollView(this);LinearLayout box=new LinearLayout(this);box.setPadding(28,12,28,12);box.setOrientation(LinearLayout.VERTICAL);scroll.addView(box);
        TextView help=new TextView(this);help.setText("首次使用：\n1. 打开高德开放平台并注册 / 登录。\n2. 在“控制台 → 应用管理 → 我的应用”创建应用。\n3. 添加 Key，服务平台选择“Web端（JS API）”，不要选 Android。\n4. 将 Key 和安全密钥 securityJsCode 填到下面。\n\n如配置了域名白名单，请加入 runlab.local。账号、实名认证、配额或收费以高德当前要求为准。\n密钥仅保存在本应用内，用于向高德请求地图。地图浏览会将视野和搜索词发给高德。\n申请教程见项目内 MAP_GUIDE.md。");box.addView(help);
        EditText key=new EditText(this);key.setSingleLine();key.setHint("高德 Web端（JS API）Key");key.setText(prefs().getString("key",""));box.addView(key);
        EditText security=new EditText(this);security.setSingleLine();security.setInputType(129);security.setHint("安全密钥 securityJsCode");security.setText(prefs().getString("security",""));box.addView(security);
        Button link=new Button(this);link.setText("打开高德开放平台");link.setOnClickListener(v->{try{startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse("https://console.amap.com/dev/key/app")));}catch(Exception e){Toast.makeText(this,"请在浏览器打开 console.amap.com",Toast.LENGTH_LONG).show();}});box.addView(link);
        AlertDialog dialog=new AlertDialog.Builder(this).setTitle("配置高德地图").setView(scroll).setPositiveButton("保存并加载",null).setNegativeButton("稍后",null).setNeutralButton("清除密钥",(d,w)->{prefs().edit().clear().apply();load();}).create();
        dialog.setOnShowListener(d->dialog.getButton(-1).setOnClickListener(v->{
            String k=key.getText().toString().trim(),secret=security.getText().toString().trim();
            if(!k.matches("[a-zA-Z0-9_-]{10,128}")||!secret.matches("[a-zA-Z0-9_-]{10,128}")){
                Toast.makeText(this,"请填写有效的 Key 和安全密钥",Toast.LENGTH_LONG).show();return;
            }
            prefs().edit().putString("key",k).putString("security",secret).apply();dialog.dismiss();load();
        }));dialog.show();
    }
    private final class Bridge {
        @JavascriptInterface public void save(String payload){
            if(payload==null||payload.length()>1500000)return;
            runOnUiThread(()->{try{
                if(!trustedPage)throw new IllegalArgumentException("页面未就绪");
                JSONObject json=new JSONObject(payload);String mode=json.getString("mode");
                if(!java.util.Arrays.asList("point","track","line","draw","circle").contains(mode))throw new IllegalArgumentException("未知绘制方式");
                JSONArray center=json.getJSONArray("center");double a=center.getDouble(0),b=center.getDouble(1);
                if(!Double.isFinite(a)||!Double.isFinite(b)||Math.abs(a)>80||Math.abs(b)>180)throw new IllegalArgumentException("选点坐标无效");
                double[] wgs=MapGeometry.toWgs(a,b);Intent result=new Intent().putExtra("lat",wgs[0]).putExtra("lon",wgs[1]);
                if(!"point".equals(mode)){
                    JSONArray pts=json.getJSONArray("points");if(pts.length()<2||pts.length()>10000)throw new IllegalArgumentException("请绘制 2–10000 个路线点");
                    MapRouteStore.Route r=new MapRouteStore.Route();r.points=new double[pts.length()][2];r.closed=json.getBoolean("closed");
                    r.name="track".equals(mode)?"田径场跑道":"circle".equals(mode)?"地图圆形路线":"draw".equals(mode)?"地图手绘路线":"地图连线路线";
                    r.mode=mode;r.laps=json.optInt("laps",0);
                    if("track".equals(mode)){
                        JSONObject e=json.getJSONObject("editor");double perimeter=e.getDouble("perimeter"),ratio=e.getDouble("ratio"),bearing=e.getDouble("bearing");
                        if(!Double.isFinite(perimeter)||perimeter<40||perimeter>20000||!Double.isFinite(ratio)||ratio<.1||ratio>.85||!Double.isFinite(bearing)||bearing<0||bearing>360)throw new IllegalArgumentException("跑道大小或方向无效");
                        r.editor=new JSONObject().put("center",new JSONArray().put(wgs[0]).put(wgs[1])).put("perimeter",perimeter).put("ratio",ratio).put("bearing",bearing);
                    }
                    for(int i=0;i<pts.length();i++){JSONArray p=pts.getJSONArray(i);double la=p.getDouble(0),lo=p.getDouble(1);
                        if(!Double.isFinite(la)||!Double.isFinite(lo)||Math.abs(la)>80||Math.abs(lo)>180)throw new IllegalArgumentException("路线坐标无效");r.points[i]=MapGeometry.toWgs(la,lo);}
                    MapRouteStore.write(MapActivity.this,r);result.putExtra("route",true);
                }
                setResult(RESULT_OK,result);finish();
            }catch(Exception e){new AlertDialog.Builder(MapActivity.this).setTitle("无法保存路线").setMessage(e.getMessage()).setPositiveButton("知道了",null).show();}});
        }
    }
    @Override protected void onDestroy(){if(web!=null){trustedPage=false;web.removeJavascriptInterface("RouteApp");web.stopLoading();web.destroy();}super.onDestroy();}
}
