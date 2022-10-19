import java.util.Scanner;

public class friend_copy
{
    public static void main(String [] args)
    {
        Scanner in = new Scanner(System.in);

        String name = in.next();
        String strCopy = name;
        name = in.next();
        
        System.out.println("Hello " + name + " Nice to meet you!");
        System.out.println("Hello " + strCopy + " Nice to meet you!");
    }
}