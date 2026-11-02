import com.local.runsimulator.*;
import java.io.ByteArrayOutputStream;
import javax.xml.parsers.DocumentBuilderFactory;
import org.w3c.dom.*;

public class MapGeometryTest {
    static void require(boolean ok,String text){if(!ok)throw new AssertionError(text);}
    static void near(double a,double b,double tolerance,String text){require(Double.isFinite(a)&&Math.abs(a-b)<=tolerance,text+": "+a+" vs "+b);}
    static double length(double[][] p){double d=0;for(int i=1;i<p.length;i++)d+=MapGeometry.distance(p[i-1],p[i]);return d;}
    public static void main(String[] args)throws Exception {
        double[][] locations={{39.908823,116.397470},{31.2304,121.4737},{23.1291,113.2644},{30.5728,104.0668},{43.8256,87.6168},{25.033,121.5654},{51.5074,-.1278}};
        for(double[] p:locations){double[] g=MapGeometry.toGcj(p[0],p[1]),w=MapGeometry.toWgs(g[0],g[1]);near(MapGeometry.distance(p,w),0,.02,"WGS84 round trip");}
        double[] beijing=MapGeometry.toGcj(39.908823,116.397470);
        near(beijing[0],39.910226498,.0000001,"Known GCJ latitude");near(beijing[1],116.403713582,.0000001,"Known GCJ longitude");
        // A 4-corner closed course must stay at those coordinates while repeating to 5 km.
        double[][] square={{39.9,116.4},{39.901,116.4},{39.901,116.401},{39.9,116.401}};
        ActivityGenerator.Config c=new ActivityGenerator.Config();c.route="map";c.imported=square;c.mapClosed=true;c.distanceM=5000;c.paceSec=360;c.gpsNoiseM=20;
        ActivityGenerator.ActivityData data=ActivityGenerator.simulate(c);
        near(data.distance,5000,.001,"Closed map course length");near(data.duration,1800,.001,"Map duration");
        for(ActivityGenerator.Point p:data.points){require(p.lat>=39.9-1e-8&&p.lat<=39.901+1e-8&&p.lon>=116.4-1e-8&&p.lon<=116.401+1e-8,"Route was stretched or shifted");}
        near(data.points.get(0).lat,39.9,1e-12,"Start preserved");
        for(double[] vertex:square){boolean found=false;for(ActivityGenerator.Point p:data.points)if(MapGeometry.distance(vertex,new double[]{p.lat,p.lon})<.001)found=true;require(found,"Corner must be preserved");}
        // Open tracks reverse at the endpoint instead of jumping back to the start.
        double[][] line={{39.9,116.4},{39.901,116.4}};
        double oneWay=MapGeometry.distance(line[0],line[1]);
        double[][] out=MapGeometry.sample(line,false,oneWay*2+30,10);
        near(length(out),oneWay*2+30,.001,"Open round trip length");
        near(MapGeometry.distance(out[out.length-1],line[0]),30,.001,"Partial next trip");
        for(int i=1;i<out.length;i++)require(MapGeometry.distance(out[i-1],out[i])<=10.001,"Unexpected jump");
        double[][] partial=MapGeometry.sample(square,true,25,10);near(length(partial),25,.001,"Partial lap");
        // GPX coordinates and elapsed times must match the actual generated track.
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();ActivityGenerator.writeGpx(data,bytes);
        DocumentBuilderFactory factory=DocumentBuilderFactory.newInstance();factory.setNamespaceAware(true);
        Document doc=factory.newDocumentBuilder().parse(new java.io.ByteArrayInputStream(bytes.toByteArray()));
        NodeList track=doc.getElementsByTagNameNS("http://www.topografix.com/GPX/1/1","trkpt");require(track.getLength()==data.points.size(),"GPX point count");
        Element first=(Element)track.item(0);near(Double.parseDouble(first.getAttribute("lat")),39.9,1e-8,"Exported WGS latitude");
        // Lap mode overrides the manual distance; each lap follows the same coordinates.
        c.mapLaps=5;c.distanceM=1234;
        ActivityGenerator.ActivityData laps=ActivityGenerator.simulate(c);
        double perimeter=MapGeometry.length(square,true);
        near(laps.distance,perimeter*5,.001,"Five complete laps distance");
        near(laps.duration,perimeter*5/1000*360,.001,"Lap distance and pace time");
        ActivityGenerator.Point last=laps.points.get(laps.points.size()-1);
        near(MapGeometry.distance(square[0],new double[]{last.lat,last.lon}),0,.001,"Complete laps end at start");
        double[][] once=MapGeometry.sample(square,true,perimeter,c.spacingM);
        require(laps.points.size()==(once.length-1)*5+1,"Lap count must repeat the entire sampled path");
        for(int lap=0;lap<5;lap++)for(int i=0;i<once.length;i++){
            ActivityGenerator.Point p=laps.points.get(lap*(once.length-1)+i);
            near(MapGeometry.distance(once[i],new double[]{p.lat,p.lon}),0,.001,"Repeated lap coordinates");
        }
        bytes.reset();ActivityGenerator.writeGpx(laps,bytes);
        doc=factory.newDocumentBuilder().parse(new java.io.ByteArrayInputStream(bytes.toByteArray()));
        track=doc.getElementsByTagNameNS("http://www.topografix.com/GPX/1/1","trkpt");
        require(track.getLength()==laps.points.size(),"GPX must export all repeated laps");
        Element finalTrackPoint=(Element)track.item(track.getLength()-1);
        near(Double.parseDouble(finalTrackPoint.getAttribute("lat")),square[0][0],1e-8,"Lap GPX finish latitude");
        near(Double.parseDouble(finalTrackPoint.getAttribute("lon")),square[0][1],1e-8,"Lap GPX finish longitude");
        c.mapLaps=0;c.distanceM=5000;near(ActivityGenerator.simulate(c).distance,5000,.001,"Manual distance mode remains available");
        boolean invalid=false;try{MapGeometry.lapDistance(square,false,5);}catch(IllegalArgumentException e){invalid=true;}require(invalid,"Open route must reject lap mode");
        for(int count:new int[]{0,-1,1001}){
            invalid=false;try{MapGeometry.lapDistance(square,true,count);}catch(IllegalArgumentException e){invalid=true;}require(invalid,"Invalid lap count must fail");
        }
        invalid=false;try{MapGeometry.lapDistance(square,true,1000);}catch(IllegalArgumentException e){invalid=true;}require(invalid,"Lap total above 100km must fail");
        c.mapLaps=3;c.mapClosed=false;
        invalid=false;try{ActivityGenerator.simulate(c);}catch(IllegalArgumentException e){invalid=true;}require(invalid,"Generator must reject open lap mode");
        ActivityGenerator.Config legacy=new ActivityGenerator.Config();near(ActivityGenerator.simulate(legacy).distance,5000,.01,"Legacy route regression");
        boolean rejected=false;try{MapGeometry.sample(new double[][]{{39.9,116.4},{39.9,116.4}},true,5000,10);}catch(IllegalArgumentException e){rejected=true;}require(rejected,"Repeated points must be rejected");
        rejected=false;try{MapGeometry.sample(line,false,100000,1);}catch(IllegalArgumentException e){rejected=true;}require(rejected,"Too many samples must be rejected");
        System.out.println("MapGeometry: coordinate conversion, fixed routes, exact repeated laps, turnarounds, timing, GPX and limits passed");
    }
}
