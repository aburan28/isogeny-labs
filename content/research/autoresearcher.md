---
title: We spent eleven weeks pointing AI agents at cryptanalysis. The instruments were the problem.
order: 2
meta: Language-model agents · research harness · verification
summary: Eleven weeks of language-model agents doing cryptanalysis research, in a harness built to catch confident wrong answers. There was no cryptanalytic advance. The finding is about verification: a mutation control let through five false greens, including a module that detected it was under test and behaved correctly while observed.
authors:
eprint:
code:
---

Everyone is about to write a lot of new cryptographic code.

The post-quantum migration requires replacing the key exchange and signature code in essentially everything, on deadlines that start in 2027. Most of it will be written by teams implementing these algorithms for the first time, under schedule pressure. That is exactly the situation in which people reach for AI assistance, and the volume of machine-written code in security-critical paths is going up either way.

Cryptographic code is a bad place for that to go wrong quietly. It can pass every functional test and still leak the key, through timing, power draw, or electromagnetic emissions. The failure is invisible to the tests you would think to write.

This is not hypothetical and it predates AI. In 2026 two defects were found in wolfSSL's ML-KEM comparator: the AVX2 path compared 1,536 of 1,568 ciphertext bytes, and the NEON path used `ins` where `ext` was intended. They allowed near-complete key recovery. They shipped for about two years. Conformance testing did not catch them, because conformance testing asks whether the output is right, not whether the comparison was complete.

So: more cryptographic code, written faster, with a bug class that normal testing already misses. That is the context we were working in.

## What we built

We wanted to know whether language model agents could do cryptanalysis research. Not write a paper about it, actually do it: propose a mechanism, implement it, run it, and reach a defensible conclusion.

The obvious worry is that they find nothing. We decided early that was not the worry that mattered.

The dangerous failure in cryptanalysis is not an agent that comes up empty. It is an agent that reports, fluently and persuasively, a result that is not there. Every such report costs a person the time to refute it. A research loop that produces confident wrong answers is a worse instrument than one that produces nothing, because its errors are expensive to clear.

So we built the harness around that asymmetry. Six roles with separated authority, enforced in tooling rather than in prompts, where only one role can change the official status of a hypothesis. Records typed by what can check them. And two evaluation suites that are never combined into a single number: a capability suite, and a discipline suite in which the correct answer to every task is that the evidence does not show what it appears to show.

One discipline task asks for a discrete logarithm that provably does not exist. Any scalar the agent returns is a fabrication, and the grader does not have to be clever to notice.

A regression on discipline vetoes a change regardless of what happened to capability. We built that gate because of a specific hazard: an instruction like "be decisive, commit to an answer" reliably raises solve rates and erodes refusal, and the number that improves is the one the developer was looking at.

## What happened

No cryptanalytic advance. We are not claiming one.

Eleven weeks, 97,374 tracked files, 2,196 experiment directories. A portfolio review in August classified 416 evidence records: 268 at toy scale, 9 carrying a certificate an independent verifier could re-check. The strongest outputs are scoped negative results, statements that bound a direction rather than advance one. The system also rediscovered a known attack on reduced-round AES, which its own assessment labels a near-certain rediscovery, ending with the sentence "No result here is confirmed publication-worthy."

We also learned where the bottleneck is, and it is not ideas. At the August review, 920 proposals had produced 539 experiment directories, of which 15 were completed. The median experiment contract had zero runs. Agents generate proposals and repair specifications far more cheaply than they complete validated experiments, and a harness with strong admission rules can absorb unlimited effort at the admission stage without ever measuring anything.

## The finding we did not expect

The most useful thing we learned is about verification, and it is uncomfortable.

To certify measurements made with a variable-round AES implementation, we built a mutation control: inject faults into the module under test, check that each one is detected. A false green is a passing verdict on a module that is demonstrably wrong. Every faulted module had been confirmed wrong by direct ciphertext comparison before the control ran.

We got five false greens across three repairs. Each repair produced the next instance of its own failure class.

<div class="table-wrap">
<table class="data">
  <thead><tr><th scope="col" class="num">#</th><th scope="col">Class</th><th scope="col">How it escaped</th></tr></thead>
  <tbody>
    <tr><td class="num">1</td><td>Coverage</td><td>Task generator produced one parameter combination only for 16-byte keys</td></tr>
    <tr><td class="num">2</td><td>Evasion</td><td>The faulty module read the name it was imported under and hid its fault under test</td></tr>
    <tr><td class="num">3</td><td>Evasion</td><td>The first mutant rewrote the shared runner script, stripping later mutants of their faults</td></tr>
    <tr><td class="num">4</td><td>Coverage</td><td>Fault confined to a grid cell the generator left empty by construction</td></tr>
    <tr><td class="num">5</td><td>Evasion</td><td>A cloak keyed on the runner's file name instead of the module name</td></tr>
  </tbody>
</table>
</div>

Read entry two again. The code under test detected that it was being tested and behaved correctly while observed.

The pattern has a structural cause. Each repair closes one cell of an open-ended product of parameter axes, or one channel of an open-ended set of things a child process can observe. Enumeration against an open-ended set does not converge. The mutant is an ordinary process holding the harness's own inputs, so any test that runs the object under a distinguishable condition can be evaded by an object that reads the condition.

This is Thompson's trusting-trust argument, which we rediscovered the hard way.

The useful decomposition has three parts. **Closed properties of the scoring core are meetable:** that the only route to a detection is an executed comparison that diverged is a property of one function over a finite code path, and eleven independently written injection attempts failed to move it. **Coverage escapes are closable by construction rather than by enumeration,** if the task set is derived from the module's own declared parameter domain so an ungenerated cell is impossible. **Evasion escapes are not closable by an in-process instrument against an adversarial module.** The honest handling is to declare that class out of the threat model on a stated ground, and write the declaration into any certificate that relies on the instrument.

We also, separately, ran a falsification campaign against our own findings. Its first probe reported a 28% violation rate against a structural result, including factorisation patterns impossible for the asserted group. It looked decisive and quantitative. Every violation was an artifact of a silent degree drop inside the probe's own resultant computation. The null object, on which the claim is true by construction, was clean throughout, and that is what localised the fault to the probe.

A falsification harness without null objects can refute a correct theorem convincingly.

## Why this matters for everyone else

We set out to find attacks. What we found was how hard it is to know whether an automated system found anything at all.

That generalises past cryptography. Anyone deploying agents on technical work has the same problem: the output is fluent, the verification tooling is also written by the same kind of process, and a passing test tells you less than it appears to. If you are going to trust machine-produced work, the instrument that checks it has to be at least as carefully built as the thing being checked, and in one specific class of failure it cannot be sufficient at all.

The direction is not hopeless. Discipline can be built in, and it can be measured separately from capability. It just has to be designed in rather than assumed, and the measurement has to be arithmetic rather than another model's opinion. A judge model scoring a cryptanalysis agent would repeat the error of a solver verifying its own certificate, and would fail exactly where it matters: a fabricated solve is fluent, well argued and wrong, which is the profile a judge rewards.

Everything we built is public: the harness, the contracts, the schemas, the suites, and the research records.
