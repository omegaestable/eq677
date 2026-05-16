# Route pass, 2026-05-14

## Role

Historical audit pass for local proof targets. No brute-force search, SAT/SMT, ATP batch,
model enumeration, or numerical testing was used; this pass used only the existing
dossier and source lookup in the ETP blueprint. For live work, start from `RAILROAD.md`
and the period-four gate in `literature.tex`.

Notation follows `RAILROAD.md`: fix `x`, set `a=x*x`, `p=x\x`, `q=x\p=a*x=d_1=c_{d-2}`, and let `*` denote the magma operation.

## Route 1: fixed point

### Claim

The fixed-point target can be replaced by a two-step gate. Define

```text
r = q*x,
h = r*q,
ell = q\x.
```

Then

```text
x*q = p,
ell = x*h,
ell = ((x*x)*q)*(x*x),
```

and the following are equivalent:

```text
E255 at x,
q*x = x,
ell = x,
h = p.
```

So the fixed-point route is now the gate-collapse target

```text
(q*x)*q = p.
```

This is the same target as in `literature.tex`, but the useful bookkeeping is that a
failure of the gate has a name: the element `h=(q*x)*q` is a definite non-`p` preimage
satisfying `x*h=q\x`.

### Argument

The specialization of `E677` with both variables equal to `x` gives

```text
x = x*(x*((x*x)*x)) = x*(x*q),
```

hence `x*q=p` by the definition of `p=x\x`.

Next specialize `E677` with law-variable `x` and parameter `q`:

```text
x = q*(x*((q*x)*q)) = q*(x*h).
```

Therefore `q\x=x*h`, i.e. `ell=x*h`.

Finally apply the transformed identity with `y=x*x=a` and `z=x`:

```text
x = (a*x)*((a*(a*x))*a) = q*((a*q)*a),
```

so `ell=((x*x)*q)*(x*x)`.

If `q*x=x`, then `h=(q*x)*q=x*q=p`. Conversely, if `h=p`, then `ell=x*h=x*p=x`; since `ell=q\x`, this says `q*x=x`. The equivalence with `E255 at x` is the unique-witness reduction already in `literature.tex`.

### Audit

Only left division by known left-bijective translations is used. There is no right cancellation, associativity, identity element, group intuition, quotient-family identity, full-shift law, universal idempotence, or small-period claim.

### Next lemma

Prove the gate-collapse identity

```text
(q*x)*q = x\x.
```

A finite-map attack on this route should first derive an actual identity of the ETP Lemma 5.5 or 5.6 form, such as `F=F*F*G` or `F=G*F*F`, for one of the self-maps naturally attached to `x` (`R_x`, `L_x R_x`, `R_x L_x`, `L_x S`, left division by `q`, or the gate map above). Once such a self-map identity is available, the finite-map lemmas have a concrete place to engage.

## Route 2: collision lift

### Claim

The orbit collision route should be downgraded from a direct propagation route to a counting route. The reason is that every right fiber already has an injective splitter.

For fixed `x` and any `e`, let

```text
F_e = { y : y*x = e },
A_e(y) = y*e.
```

For every `y` in `F_e`,

```text
A_e(y)*y = e\x.
```

Moreover `A_e` is injective on `F_e`. Thus, if `d_i=d_j=e` with `i != j`, the existing collision lift is just this right-fiber rectangle restricted to `c_i,c_j`, and the desired equality `c_i*e=c_j*e` is exactly the thing the splitter forbids unless a separate argument has already forced the fixed point.

### Argument

If `y*x=e`, the transformed identity with parameter `y` and value `x` gives

```text
x = (y*x)*((y*(y*x))*y) = e*((y*e)*y).
```

Left division by `e` yields

```text
(y*e)*y = e\x.
```

If `y,z` lie in `F_e` and `A_e(y)=A_e(z)=s`, then

```text
s*y = e\x = s*z.
```

Left cancellation by `s` gives `y=z`. Therefore `A_e` is injective on the fiber.

For an orbit collision `d_i=d_j=e`, the elements `c_i,c_j` are in `F_e`, and the displayed identity gives

```text
(c_i*e)*c_i = e\x = (c_j*e)*c_j.
```

The separate inequality `c_i*e != c_j*e` for `i != j` is the injectivity of `A_e`.

### Audit

Only transformed `E677` and left cancellation are used. The argument respects the guardrails on right cancellation, collision propagation, the retired quotient family, and the retired full-shift law.

### Route assessment

The old direct target

```text
d_i=d_j => q*x=x or c_i*e=c_j*e
```

is still formally valid as a target, but the local fiber law shows where the useful work lies: for a genuine collision, `c_i*e` and `c_j*e` must be distinct. The route needs an additional finite counting pressure that forces the injective splitter `A_e` to land in a set too small, or it should be paired with a direct fixed-point argument.

### Next lemma

Find a finite set `B_e`, naturally attached to a nontrivial orbit collision `d_i=d_j=e`, such that

```text
A_e({ c_k : c_k*x=e }) subset B_e
```

and `|B_e|` is strictly smaller than the collided orbit fiber unless `q*x=x`.

With such a size restriction, the collision route becomes a finite counting proof.

## Route 3: right-collision constraints

### Claim

The right-collision rectangles impose a sharper constraint on any proof route that passes
through the contrary fixed-point assumption.

First, in labeled-permutation notation `a*b=sigma(a)(b)`, under the contrary assumption
at `x`, no label sends `x` to itself. Hence the column map

```text
y |-> sigma(y)(x)
```

misses `x` and has a collision. If

```text
sigma(y)(x)=sigma(z)(x)=r,
```

then the rectangle constraint forces the code condition

```text
sigma(y)(r) != sigma(z)(r),
sigma(sigma(y)(r))(y) = r\x,
sigma(sigma(z)(r))(z) = r\x.
```

Second, for a homomorphic finite fiber extension `pi : M -> G` over a positive base `G` satisfying `E255`, the contrary assumption at a lift cannot occur at the base level. If `x` lies over `g` and `q_G=(g*g)*g`, then `q_G*g=g` in the base. The lifted contrary case must make the fiber map

```text
Phi_x : pi^{-1}(q_G) -> pi^{-1}(g),
Phi_x(u)=u*x,
```

miss the point `x`. In equal-size finite fibers this forces a collision inside the base witness fiber `pi^{-1}(q_G)`, and that collision must satisfy the right-fiber rectangle from Route 2.

### Argument

The labeled-permutation statements are just the right-fiber package written with `sigma(a)=L_a`. Since each `L_a` is a permutation, this notation is always available. A collision in the column over `x` gives

```text
y*x=z*x=r.
```

The right-fiber package gives `(y*r)*y=r\x=(z*r)*z`, while injectivity of the splitter gives `y*r != z*r`. Translating `y*r` as `sigma(y)(r)` gives the displayed code condition.

For the fiber-extension statement, homomorphicity gives

```text
pi(u*x)=pi(u)*pi(x)=q_G*g=g
```

whenever `pi(u)=q_G`. Thus `Phi_x` maps the witness fiber over `q_G` into the fiber over `g`. In the lifted contrary case, no `u` satisfies `u*x=x`, so `x` is missing from the image of `Phi_x`. With equal finite fiber sizes, `Phi_x` cannot be injective. Thus there are distinct `u,v` over `q_G` with

```text
u*x=v*x=r != x,
```

and Route 2 applies to this collision.

### Audit

The argument uses only left bijectivity, transformed `E677`, homomorphic projection, finite pigeonhole reasoning, and the base fact `E255` in `G`. It respects the guardrails on right cancellation, associativity, identities, group or quasigroup intuition, the retired quotient family, and the retired full-shift law.

### Next lemma

For a nonlinear equal-fiber extension over a positive base, analyze the witness-fiber map `Phi_x`. The exact proof target is:

```text
Every non-surjective Phi_x compatible with the right-fiber rectangles violates E677 somewhere else.
```

This is narrower than a general table search: the collision must occur over the base witness `q_G`, and the splitter values `u*r` must be distinct while all diagonals `(u*r)*u` equal `r\x`.

## Global audit

This pass records one fixed-point gate, redirects the standalone collision route to a counting route, and sharpens right-collision constraints to a witness-fiber obstruction. All products above are parenthesized when ambiguity matters, every cancellation is left cancellation, and the proof guardrails from `RAILROAD.md` are respected.

## Deeper source pass addendum

### Role

Historical source pass for sharper local lemmas. The ETP blueprint source and the formal `Equation677.lean` file were checked for structural lemmas used in the dossier.

### Claim

The main dossier now includes three additional durable facts.

First, the key identity

```text
(y*(y*z))*y = z*(((y*z)*z)*(y*z))
```

follows by comparing the transformed identity with `E677` at parameter `y*z`.

Second, for fixed `x`, the map

```text
H_x(t) = (x*t)*x
```

satisfies the edge-product identity

```text
x\t = t*H_x(t).
```

It is conjugate through `L_x` to `F_x(t)=x*(t*x)`. Thus a point where the fixed-point target fails is exactly a point for which these conjugate finite maps have no fixed point; any proof via this route must rule out nontrivial `H_x`-cycles compatible with `x\t=t*H_x(t)`.

Third, the `L_x`-orbit period is never `2`.  This was later strengthened in
`literature.tex`: period `3` is impossible as well, so a point where the target has not yet been established has period at least
`4`.

### Right-collision strengthening

In labeled-permutation notation `a*b=sigma(a)(b)`, the label map is injective. If `sigma(y)=sigma(z)`, then choosing any `x` and writing `e=y*x=z*x`, the two `E677` specializations with left factors `y,z` allow left cancellation by `z`, then `x`, then `e`, giving `y=z`.

Thus a right collision at a failed fixed-point column is not just a repeated value. It is a pair of distinct permutations agreeing at `x`, separating at `r`, and satisfying

```text
sigma(y)(r) != sigma(z)(r),
sigma(sigma(y)(r))(y) = r\x = sigma(sigma(z)(r))(z).
```

### Next lemma

Rule out a nontrivial cycle of `H_x(t)=(x*t)*x` under the edge-product constraint

```text
x\t = t*H_x(t)
```

or identify the exact compatible cycle inside an injectively labeled permutation system satisfying the displayed collision code. This is now the sharp fixed-map version of the route.

## Final audit pass

### Role

Audited and cold-start ready. No mathematical retraction was found in the key identity, no-two-cycle corollary, fixed-map lemma, right-fiber splitter, or injective-label argument.

### Corrections made

The polished dossier and `RAILROAD.md` no longer present the old collision equality target as a live direct route. The collision branch is now explicitly a counting route: a proof must find a natural small set containing the splitter image `A_e(F_e)`, or derive the fixed point by some other mechanism.

### Next lemma

For a proof agent, the priority lemma in this historical pass was:

```text
No nontrivial cycle of H_x(t)=(x*t)*x is compatible with x\t=t*H_x(t),
```

or identify the exact compatible cycle inside an injectively labeled permutation system satisfying the right-collision rectangles. The newer `literature.tex` period-four gate should be tried first.