! Syntax error test: missing semicolons, bad expressions
program broken;
var a : integer
begin
  a := ;
  if a then
    write(a)
end.
