import com.local.runsimulator.RunMath;
public class RunMathTest {
    static void near(double actual,double expected,double tolerance){if(Math.abs(actual-expected)>tolerance)throw new AssertionError(actual+" != "+expected);}
    public static void main(String[] args){
        near(RunMath.pace("6:00")*5,1800,0.0001);near(1800/RunMath.pace("6:00"),5,0.0001);near(RunMath.pace("6.5"),390,0.0001);
        if(!RunMath.duration(1800).equals("00:30:00"))throw new AssertionError();
        for(String invalid:new String[]{"0","-1","NaN","Infinity","6:60","6:","1:2:3"}){boolean rejected=false;try{RunMath.pace(invalid);}catch(IllegalArgumentException e){rejected=true;}if(!rejected)throw new AssertionError(invalid);}
        double[] start=RunMath.point(39.9,116.4,400,0),end=RunMath.point(39.9,116.4,400,400);near(start[0],end[0],1e-9);near(start[1],end[1],1e-9);
        double length=0;double[] prev=start;
        for(int i=1;i<=400;i++){double[] q=RunMath.point(39.9,116.4,400,i);length+=Math.hypot((q[0]-prev[0])*111320,(q[1]-prev[1])*111320*Math.cos(Math.toRadians(39.9)));prev=q;}
        near(length,400,0.01);System.out.println("RunMath: all checks passed");
    }
}
