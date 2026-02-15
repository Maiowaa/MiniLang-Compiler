! Semantic error test: undeclared vars, type mismatches, duplicate decl
program semantic_test;
var a : integer;
var a : integer;
var b : array[5] of integer;
begin
  a := 10;
  c := 5;
  b := 3;
  b[1] := 'hello';
  a[2] := 1;
  write(a + b)
end.
