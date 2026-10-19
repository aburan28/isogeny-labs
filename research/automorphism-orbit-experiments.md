# Automorphism-aware auxiliary-curve and ECDLP experiments

Status: proposed research plan; claims and performance gains require verification.

## Motivation
The referenced paper's §§4.2–4.3 and §6, and Gaudry's follow-up §4.2, suggest exploiting automorphism orbits in index-calculus relation collection and sparse linear algebra. The reported m² benefit concerns the linear-algebra dimension/cost under appropriate assumptions, **not** an unconditional m² end-to-end speedup. Verify original citations and complexity models before publishing numerical claims.

## Experiments and acceptance criteria

### 1. Orbit-aware factor bases and relation matrices
- Implement a baseline factor base F of admissible prime divisors/points and a symmetry group A acting on F.
- Preserve **all** admissible orbit members as inputs to the decomposition/relation solver. Do not replace the solver's factor base with only canonical representatives.
- Canonicalize only the unknowns/columns in relation-matrix construction, using a representative for each orbit and explicit known scalar/log relations (including sign where appropriate).
- Verify each automorphism maps admissible factor-base elements to admissible elements and preserves the target setting; reject incompatible orbits.
- Compare rank, column count, sparsity, relation yield, decomposition success, memory and wall-clock time against baseline.
- Check automorphism-induced logarithm identities on toy groups by exhaustive discrete logs; handle stabilizers and exceptional orbits.

### 2. Hidden coordinate symmetries in auxiliary curves
- Search x -> a*x+b and x -> (a*x+b)/(c*x+d) over the base field (nonzero determinant), with compatible y substitutions.
- Symbolically verify preservation of the defining curve equation, rationality and invertibility; identify induced Jacobian endomorphisms.
- Include characteristic-two translation x -> x+1 with y adjustment as a regression case inspired by the genus-six example in the paper (§4.3, Table 1).
- Determine subgroup preservation and induced scalar on the actual prime-order target subgroup, not merely geometric automorphism order.
- For rho, report the image size of A -> Aut(<P>) ~= F_r^*, avoiding double counting coincident scalar actions.
- For index calculus, report usable factor-base divisor orbits and verified logarithm identities.
- Rank auxiliary representations jointly by genus, transfer cost, orbit compression, decomposition yield and arithmetic overhead.

### 3. Multiplicative walk algebra and cycles
- For cheap endomorphisms phi, study multipliers 1+phi^j modulo subgroup order.
- Enumerate short products; flag those equal to a symmetry scalar, identity, or zero/nonunit modulo r.
- Regression: phi²=-1 implies (1+phi)(1-phi)=2, demonstrating dependent transitions.
- Check orbit-equivalent states receive orbit-equivalent successors and distinguished-point decisions.
- Measure fruitless cycles, independent-walk useful collisions, coverage, throughput and time-to-collision.
- Compare against baseline additive rho and vetted later cycle-escape strategies; do not assume the original escape procedure remains optimal.

### 4. P-192/P-224 isogeny exclusion: verify scope
- Test the statement that an isogenous curve over the same base field cannot gain new geometric automorphism types requiring a different CM endomorphism algebra. For ordinary elliptic curves, isogenies preserve End^0 over the algebraic closure; special j=0 or 1728 automorphism types demand their corresponding CM algebras.
- Compute trace, discriminant and endomorphism-algebra restrictions for P-192 and P-224; explicitly separate geometric automorphisms, rational automorphisms, and automorphisms of auxiliary higher-genus Jacobians.
- **Do not** claim this excludes all useful symmetries after GHS transfer, extension of scalars, covers, or non-elliptic auxiliary representations. Those require separate checks.
- Provide reproducible SageMath/Magma scripts and test logs before marking the exclusion proved.

## Reproducibility
- Record curve equation, field, characteristic, group order, subgroup generator, automorphism formulas, orbit partitions and induced scalars.
- Use tiny toy curves with exhaustive verification first, then larger benchmarks.
- Publish scripts, seeds, operation counts, memory, relation matrix statistics and confidence intervals.
- Distinguish theorem/proof, experimentally observed result, and conjecture in all reports.

## Suggested deliverables
1. Automorphism enumerator and induced-subgroup-action verifier.
2. Orbit-aware decomposition and compressed-matrix prototype with baseline comparison.
3. Multiplicative-walk short-cycle detector and parallel collision benchmark.
4. P-192/P-224 exclusion note with precise assumptions and counterexample search.
5. Decision table for auxiliary curves: genus, transfer, orbit size, admissibility, effective cost.

## Source verification
- Check exact bibliographic identity and printed page references for the uploaded paper (§§2.3, 3.3, 4.2–4.3, 6, Table 1 pp.113–114).
- Identify and cite Gaudry's follow-up §4.2 and later cycle-escape work before relying on specific complexity statements.
