function F = pEq(x)
global epsilon32;
global epsilon21;
global r21;
global r32;
global s;

F = ((log(epsilon32/epsilon21)+log( ((r21^x)-s)/((r32^x)-s)))/log(r21) - x);