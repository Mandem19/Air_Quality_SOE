import java.util.Scanner;

public class compare
{
    public static void main(String [] args)
    {
        Scanner in = new Scanner(System.in);
        int number = in.nextInt();
        int number2 = in.nextInt();
        if(number == number2) {
            System.out.println("True");
        }
        else {
            System.out.println("False");
        }
        }
}