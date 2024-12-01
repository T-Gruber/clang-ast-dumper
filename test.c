
typedef unsigned char my_bool;

extern int gl_var1;
int gl_var1 = 1;
int gl_var2 = 2;
extern int gl_var3;

void func(){
    gl_var3 = gl_var1 + gl_var2;
}

int main(){

    func();

    return 0;
}