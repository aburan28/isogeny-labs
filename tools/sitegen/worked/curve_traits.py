"""Recompute the descriptive F_101 example; no discrete logarithm search."""
def compute():
    p,a,b=101,2,3
    count=lambda a,b: 1+sum((y*y-x*x*x-a*x-b)%p==0 for x in range(p) for y in range(p))
    n=count(a,b); t=p+1-n
    d=next(x for x in range(2,p) if pow(x,(p-1)//2,p)==p-1)
    twist=count(a*d*d%p,b*d*d*d%p)
    disc=t*t-4*p; delta=-16*(4*a**3+27*b*b)%p
    j=1728*4*a**3*pow(4*a**3+27*b*b,-1,p)%p
    assert twist==p+1+t and n==2**5*3 and twist==2**2*3**3
    assert disc==4**2*(-23) and delta!=0
    return {'values':{},'blocks':{'example':[
        {'p':f'For y² = x³ + {a}x + {b} over F_{p}, the build enumerates every coordinate pair and adds the identity. It also counts a quadratic twist independently.'},
        {'pre':f'N = {n} = 2^5 × 3\nt = {t}\nN_twist = {twist} = 2² × 3³\nD_pi = {disc} = 4² × (−23)\nd_K = −23, v = 4\nDelta_E = {delta} mod {p}\nj = {j} mod {p}'},
        {'p':'The group order is smooth. The discriminant decomposition describes the CM field and the Frobenius order; it does not establish the actual endomorphism-ring conductor. Here f divides 4, but further information is required to determine f. A nonzero equation discriminant establishes nonsingularity, not cryptographic security.'},
        {'note':'This is a computed teaching example. No full 30-trait evaluation of cryptographic-size curves or cryptanalytic performance experiment is claimed.','note_label':'Scope'}]}}
