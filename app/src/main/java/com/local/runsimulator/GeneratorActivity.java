package com.local.runsimulator;

import android.app.*;import android.content.*;import android.graphics.Color;import android.net.Uri;import android.os.*;import android.view.*;import android.widget.*;import java.io.*;import java.util.*;import java.time.*;import java.time.format.DateTimeFormatter;import java.util.concurrent.*;

/** Mobile UI for local GPX / FIT generation. */
public final class GeneratorActivity extends Activity {
    private EditText distance,pace,lat,lon,radius,spacing,noise,hr,maxHr,gain,cadence,title,seed;private Spinner sport,strategy,format;private TextView result,totalTime,mapSummary;private CheckBox useMap,useLaps;private EditText lapCount;private MapRouteStore.Route savedRoute;
    private TextView startTime,endTime;
    private long selectedStartMillis=System.currentTimeMillis()/1000*1000;
    private final Handler timeUi=new Handler(Looper.getMainLooper());
    private final ExecutorService timeWorker=Executors.newSingleThreadExecutor();
    private Runnable timeRefresh;private int timeRevision;private boolean formReady,destroyed;
    private Button generateButton;private File pendingExport;private String pendingSummary,pendingName,pendingType,lastType;private Uri lastUri;private boolean savePickerOpen;
    @Override public void onCreate(Bundle b){super.onCreate(b);ScrollView sc=new ScrollView(this);LinearLayout box=new LinearLayout(this);box.setOrientation(LinearLayout.VERTICAL);box.setPadding(28,36,28,28);box.setBackgroundColor(Color.rgb(246,248,250));sc.addView(box);setContentView(sc);
        txt(box,"RUN / DATA LAB · 2.0",15,Color.rgb(0,119,101));txt(box,"手机运动数据生成器",28,Color.rgb(20,35,44));txt(box,"生成 GPX / FIT 时可自行选择保存位置。支持高德地图选点、田径跑道和手绘路线；地图浏览需要联网。",14,Color.DKGRAY);
        sport=spin(box,"运动类型",new String[]{"跑步","骑行"});strategy=spin(box,"配速策略",new String[]{"匀速 constant","后半程加速 negative_split","后半程减速 positive_split","间歇 interval"});format=spin(box,"输出格式",new String[]{"GPX","FIT"});
        distance=in(box,"距离（公里）","5",false);pace=in(box,"跑步配速（分:秒/公里，也支持小数分钟）","6:00",true);
        totalTime=txt(box,"",22,Color.rgb(0,119,101));
        txt(box,"跑步开始与结束时间",20,Color.rgb(20,35,44));
        if(b!=null)selectedStartMillis=b.getLong("selectedStartMillis",selectedStartMillis);
        startTime=txt(box,"",17,Color.rgb(20,35,44));
        LinearLayout clockButtons=new LinearLayout(this);box.addView(clockButtons);
        btn(clockButtons,"选择日期",v->pickStartDate());btn(clockButtons,"选择时间",v->pickStartTime());
        btn(box,"设为当前时间",v->{selectedStartMillis=System.currentTimeMillis()/1000*1000;showStartTime();updateTotalTime();});
        endTime=txt(box,"结束时间：等待计算",19,Color.rgb(0,119,101));showStartTime();
        txt(box,"时间均为北京时间（Asia/Shanghai）。结束时间随里程、配速、圈数及策略自动更新，跨天会显示次日日期；导出文件使用这里的开始时间。",13,Color.DKGRAY);
        android.text.TextWatcher calculator=new android.text.TextWatcher(){
            public void beforeTextChanged(CharSequence s,int start,int count,int after){}
            public void onTextChanged(CharSequence s,int start,int before,int count){updateTotalTime();}
            public void afterTextChanged(android.text.Editable s){}
        };
        distance.addTextChangedListener(calculator);pace.addTextChangedListener(calculator);
        sport.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){
            public void onItemSelected(AdapterView<?> parent,View view,int position,long id){updateTotalTime();}
            public void onNothingSelected(AdapterView<?> parent){}
        });
        updateTotalTime();
        txt(box,"地图路线",20,Color.rgb(20,35,44));
        btn(box,"打开地图 · 选点 / 跑道 / 手绘",v->openMap());
        useMap=new CheckBox(this);useMap.setText("使用已保存的地图路线");box.addView(useMap);
        mapSummary=txt(box,"尚未保存地图路线",14,Color.DKGRAY);
        useLaps=new CheckBox(this);useLaps.setText("按圈数生成（自动计算总里程）");box.addView(useLaps);
        lapCount=in(box,"圈数（1–1000；仅限闭合地图路线）","1",false);lapCount.setInputType(android.text.InputType.TYPE_CLASS_NUMBER);
        useLaps.setOnCheckedChangeListener((button,checked)->updateMapControls());
        lapCount.addTextChangedListener(new android.text.TextWatcher(){
            public void beforeTextChanged(CharSequence s,int start,int count,int after){}
            public void onTextChanged(CharSequence s,int start,int before,int count){updateLapDistance();}
            public void afterTextChanged(android.text.Editable s){}
        });
        txt(box,"地图路线保留所画位置与大小，闭合路线绕圈，开放路线原路往返。采样会保留拐点，并自动关闭 GPS 噪声。",13,Color.DKGRAY);
        lat=in(box,"纬度（WGS84；默认路线圆心 / 地图路线起点）","39.9042",false);lon=in(box,"经度（WGS84）","116.4074",false);radius=in(box,"默认随机圆形半径（米；地图路线不使用）","800",false);spacing=in(box,"采样间距（米）","10",false);noise=in(box,"GPS 噪声（米；地图路线自动为 0）","3",false);hr=in(box,"平均心率","145",false);maxHr=in(box,"最大心率","190",false);gain=in(box,"总爬升（米）","50",false);cadence=in(box,"步频/踏频","170",false);title=in(box,"活动标题","模拟跑步",true);seed=in(box,"随机种子","42",false);
        useMap.setOnCheckedChangeListener((button,checked)->{getSharedPreferences("generator",MODE_PRIVATE).edit().putBoolean("useMap",checked).apply();updateMapControls();});
        refreshMapRoute(getSharedPreferences("generator",MODE_PRIVATE).getBoolean("useMap",false));
        LinearLayout acts=new LinearLayout(this);box.addView(acts);btn(acts,"预览",v->generate(true));generateButton=btn(acts,"生成并另存为",v->generate(false));btn(box,"分享最近文件",v->share());result=txt(box,"尚未生成。",15,Color.rgb(0,119,101));txt(box,"点击“生成并另存为”后，在系统保存窗口选择文件夹并确认文件名，例如保存到 Download（下载）文件夹。",13,Color.DKGRAY);txt(box,"生成文件可用于测试轨迹展示和导入流程。Keep 是否接受 GPX/FIT 取决于其当前版本支持和校验；本页面不绕过 Keep 校验。",13,Color.DKGRAY);
        if(b!=null){useLaps.setChecked(b.getBoolean("useLaps",useLaps.isChecked()));lapCount.setText(b.getString("lapCount",lapCount.getText().toString()));}
        restoreFormState(b);
        for(EditText field:formFields())if(field!=distance&&field!=pace)field.addTextChangedListener(calculator);
        strategy.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){
            public void onItemSelected(AdapterView<?> parent,View view,int position,long id){updateTotalTime();}
            public void onNothingSelected(AdapterView<?> parent){}
        });
        formReady=true;updateTotalTime();restoreExportState(b);
    }
    private static final ZoneId RUN_ZONE=ZoneId.of("Asia/Shanghai");
    private static final DateTimeFormatter CLOCK_FORMAT=DateTimeFormatter.ofPattern("uuuu-MM-dd HH:mm:ss",Locale.ROOT);
    private ZonedDateTime selectedStart(){return Instant.ofEpochMilli(selectedStartMillis).atZone(RUN_ZONE);}
    private void showStartTime(){startTime.setText("开始时间："+CLOCK_FORMAT.format(selectedStart()));}
    private void chooseStart(LocalDateTime local){
        try{
            if(local.getYear()<1990||local.getYear()>2099)throw new IllegalArgumentException("开始年份须在 1990–2099 之间");
            if(RUN_ZONE.getRules().getValidOffsets(local).isEmpty())throw new IllegalArgumentException("所选当地时间不存在，请调整时间");
            selectedStartMillis=local.atZone(RUN_ZONE).toInstant().toEpochMilli();showStartTime();updateTotalTime();
        }catch(Exception e){Toast.makeText(this,e.getMessage(),Toast.LENGTH_LONG).show();}
    }
    private void pickStartDate(){
        ZonedDateTime start=selectedStart();
        DatePickerDialog dialog=new DatePickerDialog(this,(view,year,month,day)->
                chooseStart(LocalDate.of(year,month+1,day).atTime(start.toLocalTime())),start.getYear(),start.getMonthValue()-1,start.getDayOfMonth());
        dialog.getDatePicker().setMinDate(LocalDate.of(1990,1,1).atStartOfDay(RUN_ZONE).toInstant().toEpochMilli());
        dialog.getDatePicker().setMaxDate(LocalDate.of(2099,12,31).atTime(23,59,59).atZone(RUN_ZONE).toInstant().toEpochMilli());dialog.show();
    }
    private void pickStartTime(){
        ZonedDateTime start=selectedStart();
        new TimePickerDialog(this,(view,hour,minute)->chooseStart(start.toLocalDate().atTime(hour,minute)),start.getHour(),start.getMinute(),true).show();
    }
    private EditText[] formFields(){return new EditText[]{distance,pace,lat,lon,radius,spacing,noise,hr,maxHr,gain,cadence,title,seed};}
    private void restoreFormState(Bundle state){
        if(state==null)return;String[] fields=state.getStringArray("generatorFields");EditText[] inputs=formFields();
        if(fields!=null&&fields.length==inputs.length)for(int i=0;i<inputs.length;i++)inputs[i].setText(fields[i]);
        sport.setSelection(state.getInt("sport",0));strategy.setSelection(state.getInt("strategy",0));format.setSelection(state.getInt("format",0));
        updateMapControls();
    }
    private void openMap(){
        try{
            persistMapLaps();
            double a=Double.parseDouble(lat.getText().toString()),b=Double.parseDouble(lon.getText().toString()),r=useMap.isChecked()?100:RunMath.positive(radius.getText().toString());
            if(!Double.isFinite(a)||!Double.isFinite(b)||Math.abs(a)>80||Math.abs(b)>180)throw new IllegalArgumentException("请填写有效的经纬度");
            startActivityForResult(new Intent(this,MapActivity.class).putExtra("lat",a).putExtra("lon",b).putExtra("radius",Math.max(10,Math.min(20000,r))),40);
        }catch(Exception e){new AlertDialog.Builder(this).setTitle("无法打开地图").setMessage("请检查坐标、半径或圈数："+e.getMessage()).setPositiveButton("知道了",null).show();}
    }
    private void refreshMapRoute(boolean enabled){
        try{
            MapRouteStore.Route r=MapRouteStore.read(this);savedRoute=r;
            if(r==null){useMap.setChecked(false);useMap.setEnabled(false);mapSummary.setText("尚未保存地图路线；打开地图后可搜索地点并绘制。");}
            else{useMap.setEnabled(true);useMap.setChecked(enabled);mapSummary.setText(r.name+" · "+(r.closed?"单圈":"单程")+String.format(Locale.ROOT," %.1f 米 · %,d 个控制点",MapRouteStore.length(r),r.points.length));
                useLaps.setChecked(enabled&&r.laps>0);lapCount.setText(Integer.toString(r.laps>0?r.laps:1));
                if(enabled){lat.setText(String.format(Locale.ROOT,"%.8f",r.points[0][0]));lon.setText(String.format(Locale.ROOT,"%.8f",r.points[0][1]));}}
        }catch(Exception e){savedRoute=null;useMap.setChecked(false);useMap.setEnabled(false);mapSummary.setText("保存的路线无法读取，请重新绘制。");}
        updateMapControls();
    }
    private void updateMapControls(){
        boolean enabled=!useMap.isChecked();lat.setEnabled(enabled);lon.setEnabled(enabled);radius.setEnabled(enabled);noise.setEnabled(enabled);
        boolean available=!enabled&&savedRoute!=null&&savedRoute.closed;
        useLaps.setEnabled(available);if(!available)useLaps.setChecked(false);
        lapCount.setEnabled(available&&useLaps.isChecked());distance.setEnabled(!useLaps.isChecked());updateLapDistance();
    }
    private int selectedLaps(){
        try{int n=Integer.parseInt(lapCount.getText().toString().trim());if(n>=1&&n<=1000)return n;}catch(NumberFormatException ignored){}
        throw new IllegalArgumentException("圈数请输入 1–1000 的整数");
    }
    private double lapDistance(){
        if(savedRoute==null)throw new IllegalArgumentException("请先保存闭合地图路线");
        return MapGeometry.lapDistance(savedRoute.points,savedRoute.closed,selectedLaps());
    }
    private void updateLapDistance(){
        if(useLaps==null||lapCount==null)return;
        if(useLaps.isChecked()){
            try{double meters=lapDistance();distance.setText(String.format(Locale.ROOT,"%.6f",meters/1000));
                mapSummary.setText(savedRoute.name+String.format(Locale.ROOT," · 单圈 %.1f 米 × %d 圈 = %.3f 公里",MapRouteStore.length(savedRoute),selectedLaps(),meters/1000));
            }catch(IllegalArgumentException e){mapSummary.setText(e.getMessage());}
        }else if(savedRoute!=null)mapSummary.setText(savedRoute.name+String.format(Locale.ROOT," · %s %.1f 米 · %,d 个控制点",savedRoute.closed?"单圈":"单程",MapRouteStore.length(savedRoute),savedRoute.points.length));
        updateTotalTime();
    }
    private void persistMapLaps()throws Exception{
        if(useMap.isChecked()&&savedRoute!=null){
            int n=useLaps.isChecked()?selectedLaps():0;if(n>0)lapDistance();
            if(savedRoute.laps!=n){savedRoute.laps=n;MapRouteStore.write(this,savedRoute);}
        }
    }
    @Override protected void onActivityResult(int request,int code,Intent data){
        super.onActivityResult(request,code,data);
        if(request==41){completeExport(code,data);return;}
        if(request!=40||code!=RESULT_OK||data==null)return;
        lat.setText(String.format(Locale.ROOT,"%.8f",data.getDoubleExtra("lat",39.9042)));lon.setText(String.format(Locale.ROOT,"%.8f",data.getDoubleExtra("lon",116.4074)));
        refreshMapRoute(data.getBooleanExtra("route",false));
        getSharedPreferences("generator",MODE_PRIVATE).edit().putBoolean("useMap",useMap.isChecked()).apply();
    }
    private void updateTotalTime(){
        if(!formReady||destroyed)return;
        final int revision=++timeRevision;
        if(timeRefresh!=null)timeUi.removeCallbacks(timeRefresh);
        totalTime.setText("正在计算运动时长…");endTime.setText("结束时间：计算中…");
        timeRefresh=()->{
            final ActivityGenerator.Config config;
            try{config=cfg(false);}catch(Exception e){showTimeError(e);return;}
            timeWorker.execute(()->{
                try{
                    ActivityGenerator.ActivityData data=ActivityGenerator.simulate(config);
                    timeUi.post(()->{if(destroyed||revision!=timeRevision)return;
                        totalTime.setText("运动总时间："+RunMath.duration(data.duration));
                        endTime.setText("结束时间："+data.endTimeText());
                    });
                }catch(Exception e){timeUi.post(()->{if(!destroyed&&revision==timeRevision)showTimeError(e);});}
            });
        };
        timeUi.postDelayed(timeRefresh,300);
    }
    private void showTimeError(Exception e){
        totalTime.setText("总时间：--:--:--");endTime.setText("结束时间：待填写有效参数\n"+(e instanceof NumberFormatException?"请填写完整、有效的数字":e.getMessage()==null?"请检查输入":e.getMessage()));
    }
    @Override protected void onDestroy(){destroyed=true;timeUi.removeCallbacksAndMessages(null);timeWorker.shutdownNow();super.onDestroy();}
    private TextView txt(LinearLayout p,String s,int size,int color){TextView t=new TextView(this);t.setText(s);t.setTextSize(size);t.setTextColor(color);t.setPadding(0,8,0,12);p.addView(t);return t;}
    private EditText in(LinearLayout p,String label,String initial,boolean text){txt(p,label,13,Color.DKGRAY);EditText e=new EditText(this);e.setSingleLine();e.setText(initial);e.setInputType(text?android.text.InputType.TYPE_CLASS_TEXT:android.text.InputType.TYPE_CLASS_NUMBER|android.text.InputType.TYPE_NUMBER_FLAG_DECIMAL);p.addView(e);return e;}
    private Spinner spin(LinearLayout p,String label,String[] vals){txt(p,label,13,Color.DKGRAY);Spinner s=new Spinner(this);s.setAdapter(new ArrayAdapter<String>(this,android.R.layout.simple_spinner_dropdown_item,vals));p.addView(s);return s;}
    private Button btn(LinearLayout p,String label,View.OnClickListener l){Button b=new Button(this);b.setText(label);b.setAllCaps(false);b.setOnClickListener(l);p.addView(b,new LinearLayout.LayoutParams(p.getOrientation()==LinearLayout.HORIZONTAL?0:-1,-2,p.getOrientation()==LinearLayout.HORIZONTAL?1:0));return b;}
    private ActivityGenerator.Config cfg(boolean persist){try{if(persist)persistMapLaps();}catch(Exception e){throw new IllegalArgumentException(e.getMessage());}ActivityGenerator.Config c=new ActivityGenerator.Config();c.cycling=sport.getSelectedItemPosition()==1;c.distanceM=Double.parseDouble(distance.getText().toString())*1000;c.paceSec=RunMath.pace(pace.getText().toString());c.lat=Double.parseDouble(lat.getText().toString());c.lon=Double.parseDouble(lon.getText().toString());c.radiusM=useMap.isChecked()?800:Double.parseDouble(radius.getText().toString());c.spacingM=Double.parseDouble(spacing.getText().toString());c.gpsNoiseM=useMap.isChecked()?0:Double.parseDouble(noise.getText().toString());c.hrAvg=Double.parseDouble(hr.getText().toString());c.hrMax=Double.parseDouble(maxHr.getText().toString());c.gain=Double.parseDouble(gain.getText().toString());c.cadence=(int)Double.parseDouble(cadence.getText().toString());c.title=title.getText().toString();c.seed=Long.parseLong(seed.getText().toString());String x=(String)strategy.getSelectedItem();c.strategy=x.substring(x.lastIndexOf(' ')+1);c.startMillis=selectedStartMillis;c.timezone=RUN_ZONE.getId();
        if(useMap.isChecked()){try{MapRouteStore.Route r=savedRoute;if(r==null)throw new IllegalArgumentException("请先保存地图路线");c.route="map";c.imported=r.points;c.mapClosed=r.closed;c.mapLaps=useLaps.isChecked()?selectedLaps():0;if(c.mapLaps>0)c.distanceM=MapGeometry.lapDistance(r.points,r.closed,c.mapLaps);c.gpsNoiseM=0;c.lat=r.points[0][0];c.lon=r.points[0][1];}catch(Exception e){throw new IllegalArgumentException("地图路线无法读取，请重新绘制："+e.getMessage());}}
        return c;}
    private void generate(boolean preview){
        if(savePickerOpen){Toast.makeText(this,"请先完成或取消当前保存",Toast.LENGTH_SHORT).show();return;}
        try{
            if(pendingExport!=null&&!preview){launchSavePicker();return;}
            if(pendingExport!=null){Toast.makeText(this,"请先保存当前文件，或重新选择保存位置后取消",Toast.LENGTH_SHORT).show();return;}
            ActivityGenerator.ActivityData d=ActivityGenerator.simulate(cfg(true));result.setText(d.summary());
            if(preview){Toast.makeText(this,"参数有效，尚未写文件",Toast.LENGTH_SHORT).show();return;}
            String ext=format.getSelectedItemPosition()==0?"gpx":"fit";
            pendingExport=File.createTempFile("run-export-","."+ext,getCacheDir());
            try(FileOutputStream out=new FileOutputStream(pendingExport)){
                if("gpx".equals(ext))ActivityGenerator.writeGpx(d,out);else FitWriter.write(d,out);
            }
            pendingSummary=d.summary();pendingName=ActivityGenerator.filename(d.config.title,ext);
            pendingType="gpx".equals(ext)?"application/gpx+xml":"application/vnd.ant.fit";
            launchSavePicker();
        }catch(Exception e){clearPendingExport();new AlertDialog.Builder(this).setTitle("无法生成或打开保存窗口").setMessage(e.getMessage()).setPositiveButton("知道了",null).show();}
    }
    private void launchSavePicker(){
        Intent save=new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE)
                .setType(pendingType).putExtra(Intent.EXTRA_TITLE,pendingName);
        if(lastUri!=null)save.putExtra(android.provider.DocumentsContract.EXTRA_INITIAL_URI,lastUri);
        savePickerOpen=true;generateButton.setEnabled(false);result.setText(pendingSummary+"\n\n请选择保存文件夹和文件名，并点击系统窗口中的“保存”。");
        try{startActivityForResult(save,41);}catch(ActivityNotFoundException e){savePickerOpen=false;throw new IllegalArgumentException("手机的系统文件管理器不可用，请启用系统“文件”或“文档”应用后重试。",e);}
    }
    private void completeExport(int code,Intent data){
        savePickerOpen=false;
        if(code!=RESULT_OK||data==null||data.getData()==null){
            String summary=pendingSummary;clearPendingExport();result.setText((summary==null?"":summary+"\n\n")+"已取消保存，未导出新文件。");return;
        }
        Uri destination=data.getData();
        try{
            if(pendingExport==null||!pendingExport.isFile())throw new IOException("待保存数据已失效，请重新生成文件。");
            try(InputStream in=new FileInputStream(pendingExport);OutputStream out=getContentResolver().openOutputStream(destination,"wt")){
                if(out==null)throw new IOException("无法写入所选位置，请换一个文件夹。");
                byte[] buffer=new byte[32768];int count;while((count=in.read(buffer))!=-1)out.write(buffer,0,count);
            }
            rememberSavedDocument(destination,data.getFlags());lastUri=destination;lastType=pendingType;
            String name=documentName(destination,pendingName);
            String location="保存在系统保存窗口中选择的文件夹，可用手机“文件管理”查找。";
            if("com.android.externalstorage.documents".equals(destination.getAuthority())){
                try{String id=android.provider.DocumentsContract.getDocumentId(destination);int colon=id.indexOf(':');
                    if(colon>=0)location="保存位置："+(id.startsWith("primary:")?"内部存储/":"存储卷 "+id.substring(0,colon)+"/")+id.substring(colon+1);
                }catch(Exception ignored){}
            }
            result.setText(pendingSummary+"\n\n已保存："+name+"\n"+location);
            clearPendingExport();Toast.makeText(this,"文件已保存到你选择的位置",Toast.LENGTH_LONG).show();
        }catch(Exception e){
            result.setText((pendingSummary==null?"":pendingSummary+"\n\n")+"保存未完成，目标文件可能不完整。");
            AlertDialog.Builder dialog=new AlertDialog.Builder(this).setTitle("保存失败").setMessage(e.getMessage())
                    .setNegativeButton("取消保存",(d,w)->clearPendingExport());
            if(pendingExport!=null&&pendingExport.isFile())dialog.setPositiveButton("重新选择位置",(d,w)->{
                try{launchSavePicker();}catch(Exception retry){clearPendingExport();Toast.makeText(this,retry.getMessage(),Toast.LENGTH_LONG).show();}
            });
            else {clearPendingExport();dialog.setPositiveButton("知道了",null);}
            dialog.setOnCancelListener(d->clearPendingExport()).show();
        }
    }
    private String documentName(Uri uri,String fallback){
        try(android.database.Cursor cursor=getContentResolver().query(uri,new String[]{android.provider.OpenableColumns.DISPLAY_NAME},null,null,null)){
            if(cursor!=null&&cursor.moveToFirst()){String name=cursor.getString(0);if(name!=null&&!name.isEmpty())return name;}
        }catch(Exception ignored){}return fallback;
    }
    private void rememberSavedDocument(Uri uri,int flags){
        android.content.SharedPreferences prefs=getSharedPreferences("exports",MODE_PRIVATE);String previous=prefs.getString("uri",null);
        boolean persisted=false;
        try{int granted=flags&(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
            if((flags&Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION)!=0&&(granted&Intent.FLAG_GRANT_READ_URI_PERMISSION)!=0){
                getContentResolver().takePersistableUriPermission(uri,granted);persisted=true;
            }
        }catch(SecurityException ignored){}
        if(persisted)prefs.edit().putString("uri",uri.toString()).putString("type",pendingType).apply();
        else prefs.edit().clear().apply();
        if(previous!=null&&!previous.equals(uri.toString())){
            try{getContentResolver().releasePersistableUriPermission(Uri.parse(previous),Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_WRITE_URI_PERMISSION);}catch(SecurityException ignored){}
        }
    }
    private void clearPendingExport(){
        if(pendingExport!=null)pendingExport.delete();pendingExport=null;pendingSummary=null;pendingName=null;pendingType=null;savePickerOpen=false;
        if(generateButton!=null)generateButton.setEnabled(true);
    }
    private void restoreExportState(Bundle state){
        android.content.SharedPreferences prefs=getSharedPreferences("exports",MODE_PRIVATE);
        String savedUri=state==null?prefs.getString("uri",null):state.getString("savedUri",prefs.getString("uri",null));
        if(savedUri!=null)lastUri=Uri.parse(savedUri);lastType=state==null?prefs.getString("type","application/gpx+xml"):state.getString("savedType","application/gpx+xml");
        if(state==null)return;
        result.setText(state.getString("exportResult","尚未生成。"));
        String pending=state.getString("pendingFile");
        if(pending!=null&&pending.matches("run-export-[a-zA-Z0-9_-]+\\.(gpx|fit)")){
            pendingExport=new File(getCacheDir(),pending);pendingSummary=state.getString("pendingSummary","");
            pendingName=state.getString("pendingName","Activity.gpx");pendingType=state.getString("pendingType","application/gpx+xml");
            savePickerOpen=state.getBoolean("savePickerOpen",false);generateButton.setEnabled(!savePickerOpen);
        }
    }
    @Override protected void onSaveInstanceState(Bundle out){
        super.onSaveInstanceState(out);out.putLong("selectedStartMillis",selectedStartMillis);
        EditText[] inputs=formFields();String[] fields=new String[inputs.length];for(int i=0;i<inputs.length;i++)fields[i]=inputs[i].getText().toString();
        out.putStringArray("generatorFields",fields);out.putInt("sport",sport.getSelectedItemPosition());out.putInt("strategy",strategy.getSelectedItemPosition());out.putInt("format",format.getSelectedItemPosition());out.putBoolean("useLaps",useLaps.isChecked());out.putString("lapCount",lapCount.getText().toString());out.putString("exportResult",result.getText().toString());
        if(lastUri!=null){out.putString("savedUri",lastUri.toString());out.putString("savedType",lastType);}
        if(pendingExport!=null){out.putString("pendingFile",pendingExport.getName());out.putString("pendingSummary",pendingSummary);out.putString("pendingName",pendingName);out.putString("pendingType",pendingType);out.putBoolean("savePickerOpen",savePickerOpen);}
    }
    private void share(){try{
        if(lastUri==null)throw new IllegalArgumentException("请先生成并保存文件");
        try(android.os.ParcelFileDescriptor fd=getContentResolver().openFileDescriptor(lastUri,"r")){if(fd==null)throw new IOException("文件不可读");}
        Intent i=new Intent(Intent.ACTION_SEND).setType(lastType).putExtra(Intent.EXTRA_STREAM,lastUri)
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        i.setClipData(ClipData.newRawUri("运动文件",lastUri));
        startActivity(Intent.createChooser(i,"分享已保存的运动文件"));
    }catch(Exception e){new AlertDialog.Builder(this).setTitle("无法分享").setMessage("请确认文件仍在原位置且可读取。"+"\n"+e.getMessage()).setPositiveButton("知道了",null).show();}}
}
