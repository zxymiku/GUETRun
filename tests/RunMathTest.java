import com.local.runsimulator.RunMath;
public class RunMathTest {
    static void near(double actual,double expected,double tolerance){if(Math.abs(actual-expected)>tolerance)throw new AssertionError(actual+" != "+expected);}
    public static void main(String[] args){
        near(RunMath.pace("6:00")*5,1800,0.0001);near(1800/RunMath.pace("6:00"),5,0.0001);near(RunMath.pace("6.5"),390,0.0001);
        if(!RunMath.duration(1800).equals("00:30:00"))throw new AssertionError();
        for(String invalid:new String[]{"0","-1","NaN","Infinity","6:60","6:","1:2:3"}){boolean rejected=false;try{RunMath.pace(invalid);}catch(IllegalArgumentException e){rejected=true;}if(!rejected)throw new AssertionError(invalid);}
        System.out.println("RunMath: all checks passed");
    }
}
