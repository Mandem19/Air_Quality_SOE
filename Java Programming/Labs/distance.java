
import java.util.Scanner;
public class DistanceBwPoint
{
	public static void main(String arg[])
	
	{
        int x1;
        int x2;
        int y1;
        int y2;
        
        double dis;
        Scanner in = new Scanner(System.in);
        System.out.println("enter x1 point");
        
        x1=in.nextInt();
        System.out.println("enter y1 point");
        y1=in.nextInt();
        System.out.println("enter x2point");
        x2=in.nextInt();
        System.out.println("enter y2 point");
        y2=in.nextInt();
        dis=Math.sqrt((x2-x1)*(x2-x1) + (y2-y1)*(y2-y1));
        System.out.println("distancebetween"+"("+x1+","+y1+"),"+"("+x2+","+y2+")===>"+dis);
 
	}
 
}