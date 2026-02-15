program fib;
var a, b, temp, i : integer;
begin
  a := 0;
  b := 1;
  i := 10;
  while i > 0 do
  begin
    temp := a + b;
    a := b;
    b := temp;
    i := i - 1
  end;
  write('Result: ', b)
end.