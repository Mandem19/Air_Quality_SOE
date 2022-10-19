import java.util.Scanner;

public class Collatz
{
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        int n = in.nextInt();
        int i = 0;
        while (n != 1) {
            if (n % 2 == 0) {
                n = (n / 2);
            } else {
                n = (3 * n + 1);
            }
            i++;
            }
            System.out.println(i);
        }
}
