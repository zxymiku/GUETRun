package com.local.runsimulator;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.time.*;
import java.util.*;

/** Minimal FIT activity encoder. Uses FIT definition/data messages and header/file CRCs. */
public final class FitWriter {
    private static final long FIT_EPOCH=631065600L;
    private final ByteArrayOutputStream data=new ByteArrayOutputStream();
    private FitWriter(){}
    private static final class Field {
        final int number,type; final byte[] bytes;
        Field(int number,int type,byte[] bytes){this.number=number;this.type=type;this.bytes=bytes;}
    }
    private static Field u8(int n,long v){return number(n,0x02,v,1);}
    private static Field en(int n,long v){return number(n,0x00,v,1);}
    private static Field u16(int n,long v){return number(n,0x84,v,2);}
    private static Field u32(int n,long v){return number(n,0x86,v,4);}
    private static Field s32(int n,long v){return number(n,0x85,v,4);}
    private static Field number(int n,int type,long v,int size){byte[] b=new byte[size];for(int i=0;i<size;i++)b[i]=(byte)(v>>(8*i));return new Field(n,type,b);}
    private static Field str(int n,String value){byte[] raw=value.getBytes(StandardCharsets.UTF_8);return new Field(n,7,Arrays.copyOf(raw,raw.length+1));}
    private void define(int local,int global,Field... fields){
        data.write(0x40|local);data.write(0);data.write(0);little(data,global,2);data.write(fields.length);
        for(Field f:fields){data.write(f.number);data.write(f.bytes.length);data.write(f.type);}
    }
    private void values(int local,Field... fields){data.write(local);for(Field f:fields)data.write(f.bytes,0,f.bytes.length);}
    private void message(int local,int global,Field... fields){define(local,global,fields);values(local,fields);}
    private static long timestamp(ActivityGenerator.ActivityData d,double elapsed){return d.config.startMillis/1000+Math.round(elapsed)-FIT_EPOCH;}
    public static void write(ActivityGenerator.ActivityData d,OutputStream out)throws IOException{
        FitWriter w=new FitWriter();ActivityGenerator.Config c=d.config;int sport=c.cycling?2:1,sub=c.treadmill?1:0;
        long start=timestamp(d,0),end=timestamp(d,d.duration),duration=Math.round(d.duration*1000),distance=Math.round(d.distance*100);
        w.message(0,0,en(0,4),u16(1,255),u16(2,1),u32(3,0x52554E4C),u32(4,start),str(8,"RunLab Simulator"));
        w.message(0,23,u32(253,start),u8(0,0),u16(2,255),u32(3,0x52554E4C),u16(4,1),u16(5,200),str(27,"RunLab Simulator"));
        w.message(0,12,en(0,sport),en(1,sub),str(3,c.cycling?"Cycling":"Running"));
        w.message(0,21,u32(253,start),en(0,0),en(1,0));
        boolean first=true;double cycles=0,maxSpeed=0;int maxHr=0,maxCad=0;
        for(int i=0;i<d.points.size();i++){
            ActivityGenerator.Point p=d.points.get(i);List<Field> fs=new ArrayList<>();
            fs.add(u32(253,timestamp(d,p.elapsed)));
            if(!c.treadmill){fs.add(s32(0,Math.round(p.lat*(2147483648.0/180))));fs.add(s32(1,Math.round(p.lon*(2147483648.0/180))));fs.add(u16(2,Math.round((p.elevation+500)*5)));}
            fs.add(u8(3,p.hr));double cad=c.cycling?p.cadence:p.cadence/2.0;fs.add(u8(4,(long)cad));
            fs.add(u32(5,Math.round(p.distance*100)));fs.add(u16(6,Math.round(p.speed*1000)));
            if(!c.cycling)fs.add(u8(53,Math.round((cad-(long)cad)*128)));
            Field[] fields=fs.toArray(new Field[0]);if(first){w.define(1,20,fields);first=false;}w.values(1,fields);
            maxSpeed=Math.max(maxSpeed,p.speed);maxHr=Math.max(maxHr,p.hr);maxCad=Math.max(maxCad,(int)cad);
            if(i>0){ActivityGenerator.Point prev=d.points.get(i-1);cycles+=(p.cadence+prev.cadence)/2.0*(p.elapsed-prev.elapsed)/60/(c.cycling?1:2);}
        }
        long avgCad=Math.round(cycles*60/d.duration),avgSpeed=Math.round(d.distance/d.duration*1000),maxSpeedRaw=Math.round(maxSpeed*1000);
        w.message(0,21,u32(253,end),en(0,0),en(1,4));
        w.message(0,19,u16(254,0),u32(253,end),u32(2,start),u32(7,duration),u32(8,duration),u32(9,distance),u32(10,Math.round(cycles)),u16(13,avgSpeed),u16(14,maxSpeedRaw),u8(15,Math.round(d.avgHr)),u8(16,maxHr),u8(17,avgCad),u8(18,maxCad),en(25,sport),en(26,sub));
        w.message(0,18,u16(254,0),u32(253,end),u32(2,start),en(5,sport),en(6,sub),u32(7,duration),u32(8,duration),u32(9,distance),u32(10,Math.round(cycles)),u16(14,avgSpeed),u16(15,maxSpeedRaw),u8(16,Math.round(d.avgHr)),u8(17,maxHr),u8(18,avgCad),u8(19,maxCad),u16(22,Math.round(d.ascent)),u16(23,Math.round(descent(d))),u16(25,0),u16(26,1));
        ZoneId zone=ZoneId.of(c.timezone);long offset=Instant.ofEpochMilli(c.startMillis+Math.round(d.duration*1000)).atZone(zone).getOffset().getTotalSeconds();
        w.message(0,34,u32(253,end),u32(0,duration),u16(1,1),en(2,0),en(3,26),en(4,1),u32(5,end+offset));
        byte[] payload=w.data.toByteArray();ByteArrayOutputStream full=new ByteArrayOutputStream();
        full.write(14);full.write(0x20);little(full,2184,2);little(full,payload.length,4);full.write(new byte[]{'.','F','I','T'});
        little(full,crc(full.toByteArray()),2);full.write(payload);byte[] bytes=full.toByteArray();out.write(bytes);little(out,crc(bytes),2);
    }
    private static double descent(ActivityGenerator.ActivityData d){double sum=0;for(int i=1;i<d.points.size();i++)sum+=Math.max(0,d.points.get(i-1).elevation-d.points.get(i).elevation);return sum;}
    public static int crc(byte[] bytes){int c=0;for(byte b:bytes){c^=b&255;for(int bit=0;bit<8;bit++)c=(c&1)!=0?(c>>>1)^0xA001:c>>>1;}return c;}
    private static void little(OutputStream out,long value,int count){try{for(int i=0;i<count;i++)out.write((int)(value>>(8*i))&255);}catch(IOException e){throw new java.io.UncheckedIOException(e);}}
}
