import java.util.Scanner;

public class year
{
    public static void main(String [] args)
    {
        Scanner in = new Scanner(System.in);
        int number = in.nextInt();
        int answer = (byte)number;
        System.out.println(answer);
        
        int number2 = in.nextInt();
        int answer2 = (short)number2;
        System.out.println(answer2);
    }

    // This is giivng us -26 as the answer instead of 2022 the short is giving us
}