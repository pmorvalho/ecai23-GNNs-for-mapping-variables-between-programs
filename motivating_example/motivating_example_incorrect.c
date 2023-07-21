void loop(int j, int l){
  while (l >= j){	  
    printf("%d\n", j);
    ++j;
  }  
}	

int main(){
  int j, l;
  scanf("%d", &l);
  loop(j, l);
  return 0;
}
