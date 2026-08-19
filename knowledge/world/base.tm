# Closed names. Open names later use intro.
# Relations: isa(NAME, rel). Add a business relation here; do not add a pred.

! rel : e
! verb : e
! person : e

! me : e
! other : e
! here : e
! now : e
! this : e
! that : e

# Default content. No learning yet: greet, and me is 机器语言TM.
! 机器语言TM : e
+ isa(me, 机器语言TM)
+ isa(机器语言TM, person)

! do : e
! to : e
! at : e
! from : e
! goal : e
! with : e
! when : e
! has : e
! cause : e
! pol : e
! than : e

+ isa(do, rel)
+ isa(to, rel)
+ isa(at, rel)
+ isa(from, rel)
+ isa(goal, rel)
+ isa(with, rel)
+ isa(when, rel)
+ isa(has, rel)
+ isa(cause, rel)
+ isa(pol, rel)
+ isa(than, rel)

! greet : e
! ask : e
! say : e
! want : e
! order : e

! yes : e
! no : e
! who : e
! where : e
! what : e
! how : e
! whenq : e

! prog : e
! pfv : e
! dur : e
! exp : e

! invent : e
! drink : e
! live : e
! make : e
! see : e
! talk : e
! think : e
! come : e
! go : e
! hit : e
! eat : e
! use : e
! call : e
! give : e
! put : e
! openv : e
! close : e
! wait : e

! n1 : e
! n2 : e
! n3 : e
! n4 : e
! n5 : e
! n6 : e
! n7 : e
! n8 : e
! n9 : e
! n10 : e

! de : e
! clf : e
! nay : e
! last : e
! focus : e
! polar : e
! copula : e

+ isa(invent, verb)
+ isa(drink, verb)
+ isa(live, verb)
+ isa(make, verb)
+ isa(see, verb)
+ isa(talk, verb)
+ isa(think, verb)
+ isa(come, verb)
+ isa(go, verb)
+ isa(hit, verb)
+ isa(eat, verb)
+ isa(use, verb)
+ isa(call, verb)
+ isa(give, verb)
+ isa(put, verb)
+ isa(openv, verb)
+ isa(close, verb)
+ isa(wait, verb)
+ isa(want, verb)
