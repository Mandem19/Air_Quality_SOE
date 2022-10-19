import java.util.Scanner;

public class firstcharacters
{
    
    public static void main(String [] args)
    {
        Scanner in = new Scanner(System.in);
        System.out.print("The person sitting next to you : ");
        String nick = in.next();
        
        
        // printing first initial
        String initial = nick.substring(1);
        System.out.print(nick + " is spelled " + initial + ".");
    }
}