! Edge-case test: deliberate lexical errors
program errors;
begin
  x := 'unterminated string
  y := 42 @ z;
  write('valid');
end.
