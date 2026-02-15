program example1;
var x, y : integer;
var arr : array[10] of integer;
begin
  x := 5;
  y := x + 3 * 2;
  if x < y then
    write(y)
  else
    write(x);
  while x > 0 do
    x := x - 1;
  read(x, y);
  write('hello\tworld\n', x + y, 42)
end.
