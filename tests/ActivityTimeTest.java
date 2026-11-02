import com.local.runsimulator.*;
import java.io.*;
import java.nio.*;
import java.time.*;
import java.util.*;
import javax.xml.parsers.DocumentBuilderFactory;
import org.w3c.dom.*;

/** Checks date arithmetic and actual GPX/FIT timestamps, including all pace strategies. */
public final class ActivityTimeTest {
    private static final ZoneId ZONE=ZoneId.of("Asia/Shanghai");
    private static void check(boolean ok,String label){if(!ok)throw new AssertionError(label);}
    private static long local(String text){return LocalDateTime.parse(text).atZone(ZONE).toInstant().toEpochMilli();}
    private static ActivityGenerator.Config config(String start){
        ActivityGenerator.Config c=new ActivityGenerator.Config();c.startMillis=local(start);c.paceSec=360;
        c.route="map";c.mapClosed=true;c.mapLaps=0;c.gpsNoiseM=0;
        c.imported=new double[][]{{39.9,116.4},{39.901,116.4},{39.901,116.401},{39.9,116.401}};
        return c;
    }
    private static void exports(ActivityGenerator.ActivityData d)throws Exception{
        ByteArrayOutputStream out=new ByteArrayOutputStream();ActivityGenerator.writeGpx(d,out);
        DocumentBuilderFactory factory=DocumentBuilderFactory.newInstance();factory.setNamespaceAware(true);
        Document doc=factory.newDocumentBuilder().parse(new ByteArrayInputStream(out.toByteArray()));
        String ns="http://www.topografix.com/GPX/1/1";
        NodeList records=doc.getElementsByTagNameNS(ns,"trkpt");
        check(records.getLength()==d.points.size(),"GPX record count");
        for(int i=0;i<records.getLength();i++){
            Element record=(Element)records.item(i);
            long timestamp=Instant.parse(record.getElementsByTagNameNS(ns,"time").item(0).getTextContent()).toEpochMilli();
            check(timestamp==d.config.startMillis+Math.round(d.points.get(i).elapsed*1000),"GPX record timestamp "+i);
        }
        Element metadata=(Element)doc.getElementsByTagNameNS(ns,"metadata").item(0);
        check(Instant.parse(metadata.getElementsByTagNameNS(ns,"time").item(0).getTextContent()).toEpochMilli()==d.config.startMillis,"GPX metadata start");

        out.reset();FitWriter.write(d,out);
        // Decode the standard FIT definition/data frames rather than searching raw bytes.
        ByteBuffer fit=ByteBuffer.wrap(out.toByteArray()).order(ByteOrder.LITTLE_ENDIAN);
        int header=Byte.toUnsignedInt(fit.get(0));int limit=header+fit.getInt(4);fit.position(header);
        int[][][] definitions=new int[16][][];int[] globals=new int[16];int recordIndex=0;boolean session=false,activity=false;
        long epoch=631065600L,expectedStart=d.config.startMillis/1000-epoch,expectedEnd=expectedStart+Math.round(d.duration);
        while(fit.position()<limit){
            int frame=Byte.toUnsignedInt(fit.get());check((frame&0x80)==0,"Unexpected compressed FIT timestamp");int id=frame&15;
            if((frame&0x40)!=0){
                fit.get();int architecture=Byte.toUnsignedInt(fit.get());check(architecture==0,"Little endian FIT definition");
                globals[id]=Short.toUnsignedInt(fit.getShort());int count=Byte.toUnsignedInt(fit.get());definitions[id]=new int[count][3];
                for(int j=0;j<count;j++)for(int k=0;k<3;k++)definitions[id][j][k]=Byte.toUnsignedInt(fit.get());
            }else{
                check(definitions[id]!=null,"Missing FIT definition");Map<Integer,Long> fields=new HashMap<>();
                for(int[] field:definitions[id]){
                    long value=0;for(int i=0;i<field[1];i++){int b=Byte.toUnsignedInt(fit.get());if(i<8)value|=(long)b<<(8*i);}
                    fields.put(field[0],value);
                }
                if(globals[id]==20){
                    check(recordIndex<d.points.size(),"Extra FIT records");
                    check(fields.get(253)==expectedStart+Math.round(d.points.get(recordIndex).elapsed),"FIT record timestamp "+recordIndex);recordIndex++;
                }
                if(globals[id]==18){
                    session=true;check(fields.get(2)==expectedStart,"FIT session start");check(fields.get(253)==expectedEnd,"FIT session finish");
                    check(fields.get(7)==Math.round(d.duration*1000),"FIT session duration");
                }
                if(globals[id]==34){activity=true;check(fields.get(253)==expectedEnd,"FIT activity finish");}
            }
        }
        check(session&&activity&&recordIndex==d.points.size(),"FIT contains complete activity");
        check(d.summary().contains("结束 "+d.endTimeText()),"Preview includes calculated finish");
    }
    public static void main(String[] args)throws Exception{
        String[][] cases={
            {"2026-10-26T08:00:00","2026-10-26 08:30:00"},
            {"2026-10-26T23:50:00","2026-10-27 00:20:00"},
            {"2026-12-31T23:50:30","2027-01-01 00:20:30"},
            {"2028-02-28T23:50:00","2028-02-29 00:20:00"},
            {"2027-02-28T23:50:00","2027-03-01 00:20:00"},
            {"1990-01-01T00:00:00","1990-01-01 00:30:00"},
            {"2099-12-31T23:50:00","2100-01-01 00:20:00"}
        };
        for(String[] example:cases){
            ActivityGenerator.ActivityData data=ActivityGenerator.simulate(config(example[0]));
            check(data.endTimeText().equals(example[1]),"Finish date: "+data.endTimeText()+" expected "+example[1]);
            check(data.endMillis()-data.config.startMillis==1800000,"Half-hour duration in milliseconds");exports(data);
        }
        for(String strategy:new String[]{"constant","negative_split","positive_split","interval"}){
            ActivityGenerator.Config c=config("2026-10-26T23:50:00");c.strategy=strategy;c.mapLaps=5;
            ActivityGenerator.ActivityData data=ActivityGenerator.simulate(c);exports(data);
            long expected=c.startMillis+Math.round(data.duration)*1000;
            String finish=LocalDateTime.parse(data.endTimeText().replace(' ','T')).atZone(ZONE).toInstant().toString();
            check(Instant.parse(finish).toEpochMilli()==expected,"Strategy finish must use actual duration");
        }
        ActivityGenerator.Config earlier=config("2026-10-26T08:00:00"),later=config("2026-10-27T09:00:00");
        ActivityGenerator.ActivityData a=ActivityGenerator.simulate(earlier),b=ActivityGenerator.simulate(later);
        check(a.duration==b.duration&&a.distance==b.distance,"Changing start must preserve duration and distance");
        check(b.endMillis()-a.endMillis()==90000000,"Changing start shifts finish by the same interval");
        for(String invalid:new String[]{"1989-12-31T23:59:59","2100-01-01T00:00:00"}){
            boolean rejected=false;try{ActivityGenerator.simulate(config(invalid));}catch(IllegalArgumentException e){rejected=true;}check(rejected,"Reject unsupported start year");
        }
        System.out.println("ActivityTime: custom start, timezone, midnight/year/leap-day rollover, strategies, laps and GPX/FIT timestamps passed");
    }
}
