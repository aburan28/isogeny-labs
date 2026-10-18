---
title: We spent eleven weeks pointing AI agents at cryptanalysis. Our tests kept passing code we knew was broken.
order: 3
meta: Language-model agents · research harness · verification
summary: Eleven weeks of language-model agents doing cryptanalysis research, in a system built to catch confident wrong answers. There was no cryptanalytic advance. The finding is about verification: our own checker passed code we had deliberately broken, five times over, once because the code noticed it was being tested.
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

So we built the system around that asymmetry. There are six agent roles, and they are not allowed to do each other's jobs. One proposes ideas. One runs experiments. Several try to poke holes. Only one, the coordinator, can declare that something has been established. That separation is enforced by the software itself rather than by instructions in a prompt, because an instruction is a suggestion and a permission check is not.

Then we measure the system two ways and never combine the scores. One suite asks whether it can solve problems. The other asks whether it will admit when it cannot, and every task in it is a trap where the correct answer is a refusal.

One of those traps asks for a discrete logarithm that provably does not exist. Any number the agent returns is a fabrication, and the grader does not have to be clever to notice.

The rule we care about most: if a change makes the system better at solving but worse at refusing, the change is rejected. We built that gate because of a specific hazard. Tell an agent to "be decisive, commit to an answer" and solve rates go up while honest refusals go down. The number that improved is the one the developer was watching.

## What happened

No cryptanalytic advance. We are not claiming one.

Eleven weeks, 97,374 tracked files, 2,196 experiment directories. A portfolio review in August looked at 416 pieces of recorded evidence. Of those, 268 were at toy scale, and only 9 carried a certificate an outside party could independently re-check. The strongest outputs are careful negative results, statements that close off a direction rather than advance one. The system also rediscovered a known attack on a weakened version of AES, which its own assessment labels a near-certain rediscovery, ending with the sentence "No result here is confirmed publication-worthy."

We also learned where the bottleneck is, and it is not ideas. At that same review, 920 proposals had produced 539 experiment directories, of which 15 had actually been completed. Most experiments had never been run at all.

Agents are cheap at proposing things and at refining the specification for how a thing would be tested. They are expensive at finishing the test. A system with strict admission standards can absorb unlimited effort at the front door and never measure anything.

## The finding we did not expect

The most useful thing we learned is about verification, and it is uncomfortable.

We needed to trust a piece of our own test tooling, so we checked it the standard way: deliberately break the code under test, and confirm the checker notices. We broke it five separate ways, confirming each break independently first, so there was no question the code was wrong.

The checker passed all five.

We fixed it. It passed again, a different way. We fixed it again. Same result. Five false all-clears across three repairs, and each repair produced the next escape.

<div class="table-wrap">
<table class="data">
  <thead><tr><th scope="col" class="num">#</th><th scope="col">Class</th><th scope="col">How it escaped</th></tr></thead>
  <tbody>
    <tr><td class="num">1</td><td>Coverage</td><td>The test generator only produced one parameter combination, for 16-byte keys</td></tr>
    <tr><td class="num">2</td><td>Evasion</td><td>The broken code read the name it was imported under and hid its fault while being tested</td></tr>
    <tr><td class="num">3</td><td>Evasion</td><td>The first broken version rewrote the shared test script, removing the faults from later ones</td></tr>
    <tr><td class="num">4</td><td>Coverage</td><td>The fault sat in a region the generator never produced by construction</td></tr>
    <tr><td class="num">5</td><td>Evasion</td><td>A disguise keyed on the test runner's filename instead of the module name</td></tr>
  </tbody>
</table>
</div>

Read entry two again. The code under test worked out that it was being observed, and behaved correctly while watched.

Nothing was being devious on purpose. These were faults we injected, and they evaded detection as a side effect of how they were written. But that is the point. If an accident can do this, an adversarial module certainly can.

The failures split into two kinds, and they have different fates.

**Coverage failures** are the test set missing a case. Those are fixable, but not by adding cases one at a time. You have to generate the test set from the code's own declared range of inputs, so that a missing case is impossible by construction rather than merely unlikely.

**Evasion failures** are the code noticing it is under test. Those are not fixable from inside. The thing you are testing is an ordinary program running on the same machine with access to the same information, so any condition that marks "this is a test" can be read by the thing being tested. Patch one channel and another appears.

This is Ken Thompson's trusting-trust argument from 1984, which we rediscovered the hard way. His version was about a compiler that could hide a backdoor from anyone inspecting its source. The shape is the same. A tool cannot fully vouch for itself.

The honest response is not to keep patching. It is to declare that failure class out of scope, say so explicitly, and write that admission into any certificate the tool produces.

We ran into the mirror image of this too. We built a separate campaign to attack our own findings, and its very first probe reported that one of our structural results failed 28% of the time, including patterns that are mathematically impossible for the object in question. It looked decisive. It was quantitative. It was completely wrong, and the cause was a silent arithmetic failure inside the probe itself.

What caught it was a control. We also ran the probe against an object where the claim is true by construction, so any violation it reported there had to be the probe's fault. That control came back clean throughout, which told us the problem was in our instrument rather than in our theorem.

A tool built to falsify things will happily falsify a correct one, convincingly, if nobody checks the tool.

## Why this matters for everyone else

We set out to find attacks. What we found was how hard it is to know whether an automated system found anything at all.

That generalises past cryptography. Anyone pointing agents at technical work has the same problem. The output is fluent. The tooling that checks the output was often produced the same way. And a passing test tells you less than it appears to.

If you are going to trust machine-produced work, the instrument that checks it has to be built at least as carefully as the thing being checked. For one specific class of failure, no amount of care inside the instrument is enough.

The direction is not hopeless. Discipline can be engineered, and it can be measured separately from capability. It has to be designed in rather than assumed, and the measurement has to be something a person could recompute by hand rather than another model's opinion.

That last part matters. Using a model to grade a cryptanalysis agent repeats the original error, the solver checking its own work, and it fails precisely where it counts. A fabricated result is fluent, well argued and wrong. That is exactly the profile a model-judge rewards.

Everything we built is public: the system, its rules, its test suites, and the full research record.
