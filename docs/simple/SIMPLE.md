# SynthProof, explained simply

## Read this and you can defend the project

You are going to present this to a faculty panel. This guide assumes you know nothing about
the topic. It explains everything from zero, in ordinary words, and then gives you more than
a hundred questions the panel might ask with an answer to each.

There is no maths you have to memorise. There are two small pieces of arithmetic, and both
are worked out for you step by step with small numbers.

**How to use this.** Read Part 1 once, slowly. Then read Part 3, the cheat sheet, twice. Then
have somebody read the questions in Part 2 at you out loud until the answers come easily.

<!--contents-->

---

## 1. The whole project in one paragraph

Hospitals, banks and governments hold data about real people. That data could answer useful
questions — which treatment works better, which transactions are fraud. But they cannot share
it, because it would expose the people inside. We are building a tool that takes such a table
and produces a **fake table** that behaves like the real one for statistics, but is safe to
share. And, most importantly, it hands you a **certificate**: a small signed file that states
in a number exactly how safe it is. Nobody currently ships that certificate.

That is the whole project. Everything else is detail.

---

## 2. The problem, as a story

Imagine a hospital in Pune with 50,000 patient records: age, area, illness, treatment,
outcome.

A university lab asks for the data to study diabetes. The hospital wants to help. But those
records belong to real people who never agreed to be looked at by strangers.

So the hospital does the obvious thing: **it deletes the names.** No names, no problem —
right?

Wrong. And we have known it is wrong since 1997.

### The famous story

In 1997 the American state of Massachusetts released hospital records for its government
employees. They removed names and addresses first. The governor publicly promised that
privacy was protected.

A student called Latanya Sweeney bought the local voter list for about twenty dollars. It had
names, addresses, birth dates and sex. The hospital file still had ZIP code, birth date and
sex — nobody had removed those, because they do not look like names.

She matched the two lists. **Exactly one person** in the voter list had the governor's ZIP
code, birth date and sex. She posted him his own medical records.

### Why it fails, in one line

Deleting a name does not delete a person. The **combination** of the columns you kept is a
fingerprint.

### Try it on yourself

Think about these four facts about you:

- your PIN code
- your birth month
- your birth date
- your birth year

Now imagine a town of one lakh (100,000) people, and start narrowing:

```calc
start                                    1,00,000 people
after PIN code   (say 15 areas)   ->        6,667
after birth month (12)            ->          556
after birth date  (31)            ->           18
after birth year  (60)            ->      about 0.3
```

By the fourth step the expected number of matching people is **less than one**. In other
words, you are almost certainly the only person who matches. And nobody used your name.

That is the problem. Not "somebody stole the name column" — **the ordinary columns are enough.**

---

## 3. Why the usual fixes do not work

People try four things. Each one breaks in a specific way.

| what people try | what it means | why it breaks |
|---|---|---|
| Remove names | Delete name, ID, address. Share the rest. | The other columns together identify people anyway. Broken in 1997, still the default. |
| Share only totals | Publish averages, never individual rows. | Ask enough overlapping totals and you can subtract your way back to one person. Also useless for training a computer model. |
| Make fake data | Learn the patterns, generate a made-up table. | Nothing stops the program from copying a real person straight into the output. See section 5. |
| Add noise properly | Use a real mathematical privacy method. | This one actually works — but existing tools give you a number nobody checks, with no proof attached. |

The last row is the important one. **The maths already exists.** What is missing is anybody
proving they used it correctly, on the file they handed you.

---

## 4. The main idea: adding noise on purpose

Here is the trick the whole field is built on. It is easier than it sounds.

### The coin-flip game

Suppose you want to survey a class and ask: *"Have you ever cheated in an exam?"* Nobody will
answer honestly, because you are writing it down.

So you change the rules. Give every student a coin and say:

1. Flip the coin where nobody can see.
2. **Heads** — answer truthfully.
3. **Tails** — flip again. Second flip heads, say "yes". Second flip tails, say "no".

Now if a student says "yes", did they cheat? **You genuinely cannot tell.** They might have
flipped heads and told the truth. Or they might have flipped tails-then-heads and said "yes"
for no reason at all. Every student has a perfect excuse.

### But you can still get the answer

Work out the chances. If a student really did cheat, they say "yes" when:

- they flip heads (chance 1/2) and tell the truth, **or**
- they flip tails then heads (chance 1/4)

So the chance a cheater says yes is 1/2 + 1/4 = **0.75**.

If a student did **not** cheat, they only say "yes" on tails-then-heads. So that chance is
**0.25**.

Now survey 1,000 students. Suppose (unknown to you) 300 really cheated.

```calc
cheaters saying yes      300 x 0.75  =  225
non-cheaters saying yes  700 x 0.25  =  175
total "yes" you hear                =  400
```

Now work backwards. Every person says yes with chance 0.25 just from the coin, plus an extra
0.5 if they are a real yes:

```calc
400  =  0.25 x 1000  +  0.5 x (true number)
400  =  250          +  0.5 x true
true =  (400 - 250) / 0.5
true =  300                       correct
```

**You got the group answer exactly right, and you learned nothing reliable about any single
student.** That is the whole idea. Everything else is a more efficient version of this trade.

---

## 5. Why "it's fake, so it's safe" is wrong

Making fake data sounds like it must be private. Nobody in the output is a real person. What
could leak?

**Two things, and both happen in practice.**

### It can copy

Nothing in "make me a similar table" forbids the program from reproducing a real row exactly.
A program that has memorised an unusual patient — 96 years old, rare illness, unusual area —
may print that person out word for word, because for an unusual person **the pattern is the
person.**

The output is labelled synthetic. The row is a real human being.

And note who is at risk: the rare, unusual people. **The ones easiest to identify are the ones
a generator is most likely to copy.**

### Statistics leak too

Even with no copying: if only one person in the data is a 92-year-old cardiologist, then a
fake table that keeps the age-and-job relationship has told you that person exists. You never
needed their row.

**So: looking realistic is not the same as being safe. You cannot see privacy by reading the
output.** That is why the rest of the project is about measuring it.

---

## 6. What "epsilon" means

You will hear the word **epsilon** (written ε). It is just a number that says how private
something is. **Smaller is safer.**

Here are three ways to think about it. Different ones click for different people — use
whichever your listener responds to.

### 1. Epsilon is a budget

You get one fixed allowance per dataset. Every question you ask of the real data spends some
of it. When it runs out, **you stop.** Not "ask more carefully" — stop. Small epsilon means a
small allowance.

### 2. Epsilon is a noise dial

Turn it down: more noise is added, the data is safer and less useful. Turn it up: less noise,
the data is sharper and less safe. **There is no setting that gives you both.** Being honest
about that trade is the point.

### 3. Epsilon is a cap on your influence

If you removed **your** row from the data and ran everything again, the answer would barely
change. Epsilon is the size of "barely". That is exactly why nobody can work backwards from
the answer to you.

### What the numbers mean

Imagine an attacker who already knows everything about everyone else, and is only trying to
work out whether **you** are in the data. Here is the best they can do:

| epsilon | best guess about you | in plain words |
|---|---|---|
| 0.1 | 52 out of 100 | barely better than tossing a coin |
| 1.0 | 73 out of 100 | a real advantage, but limited |
| 4.0 | 98 out of 100 | almost certain |
| 8.0 | 100 out of 100 | no real protection |
| a billion | 100 out of 100 | the promise says nothing at all |

A coin toss is 50 out of 100. That is the number to compare against.

**Remember the last row.** You will sometimes see a product claiming "differential privacy"
with a huge epsilon. That claim is technically true and practically empty — a number that
large permits publishing the raw data unchanged. **A privacy promise without a stated epsilon,
or with a silly one, is marketing.**

---

## 7. What our system actually does

Six steps. Only two of them cost privacy budget, and the one everybody assumes is expensive is
free.

| step | what happens | does it look at real data? | does it cost budget? |
|---|---|---|---|
| 1. Check | Reads only the column names and how many rows there are. Refuses unsafe tables. | No — never a single value | No |
| 2. Learn columns | Works out what values each column can hold. | Yes | **Yes** |
| 3. Count and blur | Counts how many people are in each group, then adds measured noise to every count. | Yes | **Yes** |
| 4. Build fake table | Builds a new table using only the blurred counts. | No | No |
| 5. Attack it | Hides known records, then attacks our own output to see what can be found. | Only the planted ones | No |
| 6. Certify | Writes and signs the certificate. | No | No |

### Three things worth understanding

**Step 1 refuses.** Give it a table with a patient-ID column and it says no, names the column,
and tells you how to fix it — **without reading a single value.** A check that had to read
your data to decide whether your data was safe would be the exact bug it exists to prevent.

**Step 2 costs, and this is our differentiator.** Finding out what values a column can hold
means looking at real people's values. Most tools do this for free and never mention it. We
either charge for it, or you tell us the columns in advance.

**Step 4 is free, and this surprises people.** Building the fake table costs nothing. Once
data has been made private, anything you calculate from it stays private. That is a proved
rule, not a shortcut. The real table stops at step 3 and goes no further.

---

## 8. The certificate — the actual product

Every packet of food you buy lists its ingredients. No dataset anywhere does. That is what we
are shipping.

Alongside the fake data, you get a small file — we call it a **Privacy Data Sheet** — that
says:

- how many rows are in the file
- **how much privacy budget was spent** (one number for the whole thing)
- how that budget was split between the steps
- **what our own attack managed to find**
- **the limit of that attack** — the most it could ever have found
- which columns you declared, and which we had to work out ourselves
- a signature, so anyone can check the file was not edited afterwards

### The most important line

That fifth one — **the limit of the attack** — is the cleverest idea in the project, so make
sure you understand it.

Suppose we attack our own data and find nothing. There are two possible reasons:

1. Nothing leaked. Good.
2. Our attack was too small to notice anything. Not good.

**Everybody reports the first and never checks which it was.** We calculate it and print it
right underneath. Because a zero that nobody can interpret is worse than no number at all.

---

## 9. What is new about this

Three things. Nothing else on the market does any of them.

**One — two numbers, one run.** The proved number (what maths guarantees) and the attacked
number (what a real attack got) come from the same pipeline, on the same file, and both land
on the certificate you receive. Today those two live in different research papers written by
different people, and neither reaches the person actually receiving the data.

**Two — we print the limit of our own attack.** Explained above. This is the claim to be
proudest of and the one to invite criticism on.

**Three — it refuses.** Unsafe tables are turned away before a single value is read, with the
offending column named and a remedy suggested. A product whose headline feature is refusing to
work is unusual, and it is deliberate.

### What is NOT new — say this before you are asked

Be honest about this. It makes you stronger, not weaker.

- The privacy arithmetic is **Google's `dp_accounting` library**. We do not write our own.
- The best generator is **AIM**, from the private-PGM authors. We use it; we did not invent it.
- The one-run attack method is from **Steinke, Nasr and Jagielski (2023)**.
- The idea that an attack has a detection limit is **known** in that literature.

**Ours is the integration, the refusal gate, the certificate, and the decision to report the
limit next to every number.** Volunteering this is far better than being caught on it.

---

## 10. Where it would be used

| sector | who holds the data | who wants it | what we unblock |
|---|---|---|---|
| Healthcare | A hospital with 50,000 diabetes records | A university lab building a risk model | A signed, defensible answer to "was it safe to share this?" |
| Banking | A bank with labelled fraud transactions | A vendor training a fraud detector | Share the patterns without exposing any customer |
| Telecom | An operator with movement data | City planners modelling transport | Population movement without individual journeys |
| Government | Census or scheme enrolment records | Open-data portals, researchers, NGOs | Publish usable data with the privacy cost printed on it |

The shape is the same everywhere: **the holder cannot prove it is safe, so nothing moves.**

---

## 11. What we build first, and what comes later

### The smallest useful version

- Upload one CSV file, with a short description of its columns
- It refuses unsafe columns, by name, and tells you how to fix them
- You choose how private you want it
- You get the fake data plus a signed certificate
- You can check the certificate with one command
- Available as a command-line tool, a web service, and a browser console

### Deliberately NOT in the first version

- Several tables joined together
- Images, free text, or time-series data
- One budget shared across many users and sessions
- Deep-learning generators

Each of those is a project on its own. **Claiming all four is the fastest way to build none of
them.** Saying this out loud is one of the strongest things you can do in a review.

### The plan, in four phases

| phase | goal | what gets built |
|---|---|---|
| 1 | Prove the core works | Budget accounting, two generators, the refusal gate |
| 2 | Make it honest | The self-attack, printing the detection limit, signed certificates |
| 3 | Make it usable | Web console, a second dataset, reproducible runs |
| 4 | Harden it | A stronger attacker, budget across sessions, a third dataset |

Notice that **"make it honest" comes before "make it usable"**. That ordering is deliberate,
and a good examiner will notice it.

---

## 12. Future plans, beyond the capstone

These are the honest next steps if the project continued.

**Short term (next few months)**

- Add a third and fourth dataset, so no conclusion rests on one source
- Build a stronger attacker, and keep printing the detection limit beside whatever it finds
- Fix the list of columns to be measured **in advance**, so no method can be scored on a
  question it chose for itself
- Add the shadow-model attack, named honestly for what it is

**Medium term (a year)**

- Budget enforced across sessions and users, so one dataset cannot be quietly drained by many
  small requests
- Multi-table support, which is genuinely hard because privacy cost spreads across joins
- A hosted service so a hospital does not have to install anything

**Longer term**

- Text and image data, which need completely different generators
- A public registry of certificates, so a released dataset's privacy claim can be looked up
- Working with a regulator to see whether a certificate like ours could count as evidence of
  compliance

**The honest limitation to keep repeating:** this is an instrument for checking releases. It
is not ready to be pointed at real patient data today, and we would rather say so than
oversell it.

---

## 13. One hundred and twenty questions, with answers

Every answer here has two parts: the answer itself, and a concrete example you can say out
loud. The example is usually the thing that makes a panel nod. Practise saying both.

### A. The basics

**1. What is your project in one sentence?**
A tool that takes a table of real people, produces a fake table that is safe to share, and
attaches a signed certificate stating exactly how private that fake table is.
*Example: a hospital hands us 50,000 patient rows and gets back 50,000 invented rows plus a
one-page certificate saying "privacy budget spent: 0.9".*

**2. What problem does it solve?**
Organisations sit on data that would answer real questions, but they cannot share it because
they have no way to prove a release is safe. We turn that unanswerable question into a signed
document.
*Example: a lab asks a hospital for diabetes records. The hospital's legal team asks "can you
prove this is safe?" Today there is no answer, so the request is refused and the research never
happens.*

**3. Who is it for?**
Anybody holding personal records who wants to share them: hospitals, banks, telecom operators,
government departments, and the researchers on the other side who need the data.
*Example: a state health department that wants to publish district-level patient data for
researchers without exposing any individual patient.*

**4. What does the user actually do, step by step?**
They upload one table, write a short description of what each column contains, choose how
private they want the output, and receive two files back: the fake data and the certificate.
*Example: upload `patients.csv`, declare "age is a number from 0 to 110, district is one of 15
values", pick a privacy setting, get `synthetic.csv` and `certificate.json`.*

**5. Why is it called SynthProof?**
"Synth" for synthetic data, "Proof" for the certificate that ships with it. The name is the
argument: synthetic data is common, shipping proof alongside it is not.
*Example: any tool can hand you a fake CSV. Ours hands you the CSV and a document you can
verify with one command.*

**6. Is this a research project or a product?**
Both. It is a working tool, and it was built to answer a research question: can a privacy claim
actually be checked by the person receiving the data?
*Example: the tool runs today and produces certificates; the research contribution is what goes
on the certificate and why.*

**7. What is synthetic data?**
A made-up table that behaves like a real one for statistics — same rough proportions, same
relationships between columns — but whose rows are not real people.
*Example: if 30% of your real patients are diabetic and older patients are more likely to be,
the fake table shows roughly 30% diabetic with the same age pattern. But no row corresponds to
an actual person.*

**8. Why not just anonymise the data?**
Because removing a name does not remove a person. The remaining ordinary columns, in
combination, still point to one individual.
*Example: delete every name from a hospital file, but leave PIN code, birth date and sex.
Anyone with a voter roll can match those three fields back to a name — which is exactly what
happened in Massachusetts in 1997.*

**9. What is differential privacy, in one line?**
A mathematical promise that whether or not any one person is in the data changes the answer by
only a tiny, measured amount.
*Example: take two versions of a hospital file — one with Priya, one without. Ask both "how
many diabetics?" If you cannot tell the two answers apart, Priya is protected.*

**10. What is epsilon?**
Epsilon is the size of that "tiny amount". It is a single number describing how much any one
person can influence the output. Smaller is safer.
*Example: at epsilon 1, an attacker who already knows everything else can guess whether you are
in the data about 73 times out of 100. A coin toss is 50. At epsilon 8 it is essentially 100.*

**11. Who chooses epsilon?**
The data owner chooses it, because it is a policy decision, not a technical one. Our job is to
charge it honestly and print what was actually spent on the certificate.
*Example: a hospital's ethics board might mandate epsilon at most 1 for patient data, while a
council publishing bus-usage counts might accept 4.*

**12. What is the certificate?**
A small signed file listing how much privacy budget was spent, how it was split across steps,
what our own attack recovered, and the limit of that attack.
*Example: it reads like a nutrition label — "records: 6,000; budget spent: 0.91; attack found:
nothing; limit of that attack: 2.25; columns you declared: 12 of 12".*

**13. Why does the certificate matter?**
Because today the privacy number exists in a research paper and never reaches the person
receiving the file. The certificate moves the claim to where the decision is actually made.
*Example: the researcher receiving the data currently has to trust an email. With a certificate
they can verify the file was not altered and see the privacy cost in writing.*

**14. Is this already used in industry?**
The underlying mathematics is — the US Census Bureau and several large technology companies use
differential privacy in production. Shipping a verifiable certificate with each release is not
something we found anywhere.
*Example: the 2020 US Census was published using differential privacy, but a member of the
public cannot download a certificate proving what was spent on their block.*

**15. How is this a capstone-level project?**
It combines four areas — statistics, cryptography, machine learning and systems engineering —
and it answers a research question with a real, falsifiable answer.
*Example: the noise sampling is statistics, the signing is cryptography, the generator is
machine learning, and the API, ledger and console are systems work.*

### B. The problem

**16. Is re-identification really a risk, or is it theoretical?**
It is documented repeatedly, over decades, on real released datasets.
*Example: Sweeney 1997 (the Massachusetts governor), Sweeney 2000 (87% of Americans unique on
three fields), the Netflix Prize in 2008 (users identified by matching public film reviews), and
a 2022 EPFL study showing synthetic-data tools did not help.*

**17. What exactly was the Sweeney result?**
Latanya Sweeney showed that about 87% of Americans are uniquely identified by ZIP code, date of
birth and sex alone — three fields nobody thinks of as identifying.
*Example: she bought a $20 voter roll, matched it against a "de-identified" hospital release,
found exactly one person with the governor's ZIP, birth date and sex, and posted him his own
medical records.*

**18. Does that apply in India?**
The principle does — a PIN code plus a full date of birth narrows a population extremely fast.
The exact 87% figure is American and we do not claim it here.
*Example: 15 PIN codes, 12 months, 31 days, 60 birth years gives 334,800 combinations. In a town
of one lakh, most combinations are used by nobody, and the ones that are used are usually used
by exactly one person.*

**19. Why can't hospitals just be careful?**
Because being careful is not provable, and the incentives only run one way — nobody is ever
blamed for refusing to share.
*Example: a data officer who approves a release and is later embarrassed loses their job. One
who refuses everything never appears in a news story. So the default is always no.*

**20. What is the cost of not sharing?**
Research is delayed or abandoned, models get trained on foreign data that does not match the
local population, and the patient gets neither the research nor real protection.
*Example: an Indian diabetes risk model trained on American data will misjudge Indian patients,
because the age and body-type patterns differ.*

**21. Isn't there a law that solves this?**
Laws say what you are permitted to share; they do not tell you how to prove a particular file is
safe. That gap is a technical one.
*Example: India's DPDP Act and Europe's GDPR both allow sharing "anonymised" data — but neither
defines a test you can run on a file to check it qualifies.*

**22. What about consent — can't you just ask patients?**
Consent is about permission, not about how much a released file reveals. You need both, and
consent alone does not bound the leak.
*Example: a patient consents to research use. That does not stop the released file from
containing their exact record, which they almost certainly did not intend.*

**23. Why is publishing only aggregates not enough?**
Because overlapping totals can be subtracted to recover individuals, and because you cannot
train a model on averages.
*Example: publish "average salary in this office is 50,000" and later "average salary excluding
the manager is 45,000". With 10 staff, you have just revealed the manager's salary exactly.*

**24. Has anyone actually been harmed by this?**
The Massachusetts case is the clearest documented one. Most incidents are never made public,
which is itself part of the problem.
*Example: the governor received his own medical records in the post as a demonstration. If a
malicious party had done it instead, nobody would ever have known.*

**25. Why has nobody fixed this already?**
The mathematics is recent and easy to implement incorrectly, and there is no commercial reward
for publishing a number that makes your product look weaker.
*Example: a vendor who honestly reports "our attack could only ever have detected a large leak"
looks worse than one who says "our attack found nothing", even though the first is more useful.*

### C. Privacy concepts

**26. Explain differential privacy to someone non-technical.**
Take two versions of a file that differ by exactly one person. Ask both the same question. If
you cannot tell the two answers apart, that person's presence did not leak.
*Example: File A has Priya, File B does not. Ask "how many diabetics?" If A says 847 and B says
846, you have learned Priya is diabetic. If both answers are blurred into a range of 800–890,
you have learned nothing about her.*

**27. Why add noise at all?**
Because an exact answer about a small group is effectively an answer about individuals.
*Example: "how many diabetics live on this street?" answered exactly, for a street of four
houses, tells you a great deal about four specific families.*

**28. Doesn't the noise make the data wrong?**
Slightly, and that is precisely the trade we manage. Group-level conclusions survive;
individual-level certainty does not, which is the point.
*Example: the true count is 847 and we report 851. A researcher studying prevalence is
unaffected. An attacker trying to confirm one person is defeated.*

**29. What is the difference between epsilon and delta?**
Epsilon is how much can leak in the normal case. Delta is a very small probability that the
promise fails entirely. We keep delta tiny.
*Example: we use delta of 1 in 100,000 — roughly the chance of a specific coin landing on its
edge. Epsilon governs the other 99,999 cases.*

**30. Why is a smaller epsilon safer?**
Because it tightens how much any one person can shift the output, leaving less for an attacker
to work backwards from.
*Example: at epsilon 0.1 your presence changes the answer so little that an attacker's guess
improves from 50-in-100 to 52-in-100. At epsilon 8 it improves to essentially certainty.*

**31. What epsilon will you use?**
That is the data owner's decision, not ours. What we guarantee is that we charge honestly and
print the amount actually spent.
*Example: if they ask for 1.0 and our calibration lands at 0.91, we print 0.91 — we never
quietly spend more than requested.*

**32. What counts as a good epsilon?**
There is no universal answer, which is why we print the odds in words rather than expecting a
reader to interpret the number.
*Example: instead of printing "epsilon = 1.0", the certificate can say "an attacker who knows
everything else can guess whether you are in this file 73 times in 100".*

**33. What is post-processing invariance?**
The rule that anything you calculate from private data stays private, because your calculation
never saw the original.
*Example: once we have blurred counts, we can build a table, plot a chart, and train a model
from them — all for free, because none of those steps can see anything the blurred counts did
not already reveal.*

**34. What is composition?**
The rule for adding up privacy cost across many operations. It is subtle, and it is where
implementations quietly go wrong.
*Example: asking twenty questions each costing 0.1 does not simply cost 2.0 — the correct total
depends on the mechanism, and getting it wrong understates your leak.*

**35. What kind of noise do you add?**
Discrete Gaussian or discrete Laplace noise — sampled directly as whole numbers rather than by
generating a decimal and rounding it.
*Example: to a true count of 847 we might add −3 to give 844. The −3 is drawn as an integer from
the start.*

**36. Why does that rounding detail matter?**
Because sampling a decimal and rounding reopens a published class of attacks that exploit how
computers store decimals.
*Example: certain decimal values are impossible to produce by rounding, so an attacker seeing
one of those gaps can infer something about the true value. Sampling integers directly leaves no
such gaps.*

**37. What is a canary?**
A record we plant in the data on purpose, so we know the truth about it and can check whether an
attack can find it.
*Example: we insert 30 invented patients, run the whole pipeline, then ask the attack "which of
these 30 were included?" If it guesses no better than chance, nothing leaked that it could see.*

**38. What is a membership inference attack?**
An attack that tries to determine whether a specific person was in the original dataset — not
what their record said, just whether they were there at all.
*Example: knowing someone was in a dataset of HIV patients is itself the sensitive fact. The
attacker does not need to read the row.*

**39. Does differential privacy stop every attack?**
It bounds what any attacker can learn about any individual, including attackers nobody has
thought of yet. It does not stop you learning true things about the population, which is the
whole point of releasing data.
*Example: an attacker can still learn "diabetes is more common over 50" from our output. They
cannot learn whether your uncle in particular is diabetic.*

**40. What if the attacker already knows a lot about me?**
The guarantee deliberately assumes the worst case: an attacker who knows every other record and
is only missing yours. That is what makes it a strong promise.
*Example: even if someone has the entire hospital file except your row, the released output
still does not tell them whether you were in it.*

### D. How the system works

**41. Walk me through the pipeline.**
Six steps: check the table is safe to attempt, learn what the columns contain, count groups and
add noise, build a fake table from those blurred counts, attack our own output, then sign a
certificate.
*Example: `patients.csv` goes in; a refusal or `synthetic.csv` plus `certificate.json` comes
out.*

**42. Which steps cost privacy budget?**
Only two: learning what values the columns hold, and counting the groups. The other four are
free.
*Example: counting how many patients fall into each age band touches real people and is charged.
Building the fake table from those blurred counts is not.*

**43. Why is building the fake table free?**
Post-processing invariance. That step only ever sees blurred counts, never the real table, so it
cannot reveal anything the counts did not already.
*Example: once we know "roughly 300 diabetics, mostly older", generating a million fake rows
from that description leaks nothing further.*

**44. What does the check step refuse?**
Identifier-like columns, free text, tables with fewer than 500 rows, and column pairs whose grid
is too large to produce useful numbers.
*Example: a `patient_id` column with 2,000 distinct values in 2,000 rows is refused outright —
one value per person is a direct identifier.*

**45. Why does the check not read the data to decide?**
Because reading your data to decide whether reading your data is safe would be the exact leak the
step exists to prevent.
*Example: it sees the column is called `patient_id` and that the schema declares 2,000 possible
values across 2,000 rows. That is enough to refuse, without opening a single cell.*

**46. What happens if my table is refused?**
You get the offending column named and a specific remedy, so the refusal is actionable rather
than a dead end.
*Example: "Column `pincode` has 2,000 distinct values across 2,000 rows. Replace it with a
coarser grouping such as district."*

**47. Why do you charge for learning the columns?**
Because working out what values a column contains means looking at real people's values. Most
tools do it for free and never mention it.
*Example: to know that `district` has 15 possible values, something had to read the district of
every patient. That is a query about real people, so it goes on the bill.*

**48. How can I avoid paying that cost?**
Declare your columns in advance. Genuinely public information costs nothing because it reveals
nothing about any individual.
*Example: "district is one of these 15 names" is public knowledge about Pune, not a fact about
any patient — so declaring it is free.*

**49. How do you attack your own data?**
We plant known records, run the full pipeline, then try to detect which of them were included
using only the released output.
*Example: plant 30 canaries, release the data, then let the attack guess. If it gets 15 of 30
right, that is chance. If it gets 29, something leaked badly.*

**50. What if the attack does find something?**
Then we report it. The number goes on the certificate either way — that is the entire
discipline.
*Example: if the attack recovers a leak, the certificate says so, and the data owner can lower
epsilon and run again.*

**51. What if the attack finds nothing?**
We report that too, together with the limit of the attack — the most it could ever have detected
given how many canaries we planted.
*Example: "attack found nothing; the most this attack could ever have detected was 2.25." Without
the second half, the first half is unreadable.*

**52. How is the certificate signed?**
With an Ed25519 digital signature, a standard modern scheme. Anyone with our public key can
verify it.
*Example: one command — `synthproof verify certificate.json --pubkey org.pub` — prints VERIFIED
or FAILED.*

**53. What stops somebody editing the certificate?**
Editing any field breaks the signature, and verification then fails loudly.
*Example: change "budget spent: 0.91" to "0.01" to look better, run verify, and it prints FAILED
— the file no longer matches what was signed.*

**54. Is it tamper-proof?**
No — tamper-**evident**, and the distinction matters. Anyone holding the signing key could
rewrite and re-sign. Key custody is an organisational control, not a cryptographic one.
*Example: we can prove nobody altered the file after signing. We cannot stop the signing
organisation itself from issuing a dishonest certificate.*

**55. What is the ledger?**
A running record of every release and what it spent, where each entry carries a fingerprint of
the entry before it, so history cannot be quietly rewritten.
*Example: delete or edit release number 3 and every entry after it stops matching, so the
tampering is visible rather than silent.*

### E. Novelty

**56. What is genuinely new here?**
Shipping both numbers — the mathematically proved bound and what a real attack recovered — on
one release, and printing the limit of our own attack beside them.
*Example: existing tools give you one number in a paper. We give you two numbers and a
statement of how far the second one could ever have reached, attached to the file.*

**57. Isn't this just a wrapper around existing libraries?**
The generators and the privacy arithmetic are existing work and we say so on the slide. The
refusal gate, the self-attack, the certificate and the limit calculation are ours.
*Example: we import Google's accounting the same way a bridge engineer buys steel. The design of
the bridge is still the work.*

**58. What did you not invent?**
Google's `dp_accounting` for the arithmetic, the AIM generator from the private-PGM authors, and
the one-run attack construction from Steinke, Nasr and Jagielski (2023).
*Example: if a panellist wants to attack our privacy mathematics, the honest answer is "attack
Google's library, because that is whose arithmetic it is".*

**59. Why is printing the attack limit important?**
Because "we attacked it and found nothing" is meaningless on its own. There are two reasons an
attack finds nothing, and only one of them is good news.
*Example: a metal detector that finds no gold might mean there is no gold — or that it can only
detect objects bigger than a brick. Everyone reports the first. We calculate which it was.*

**60. Has anybody published that idea before?**
The existence of a detection limit is known in the auditing literature and we cite it. Making it
a required field on every release is our design decision.
*Example: the underlying result is in Steinke et al. 2023 and earlier work. What is missing is
anybody putting it in front of the person receiving the data.*

**61. How do you compare with SDV?**
SDV generates synthetic data well but makes no formal privacy claim and does not attack its own
output. It is a synthesis library, not a privacy tool, and does not claim to be.
*Example: SDV will happily reproduce an unusual row if that is what the statistics suggest,
because nothing in its design forbids it.*

**62. How do you compare with Gretel or SmartNoise?**
They offer genuine formal guarantees and are serious tools. They do not attack their own output,
do not state a detection limit, and do not ship a checkable certificate.
*Example: SmartNoise will correctly tell you epsilon = 1. It will not hand the recipient a
signed file proving that is what was actually spent.*

**63. Isn't refusing to work a weakness rather than a feature?**
The opposite. A tool that silently accepts an unsafe table and produces confident-looking output
is far more dangerous than one that says no.
*Example: give a normal tool a table with a patient-ID column and it produces "synthetic"
identifiers that may be real. Ours refuses and tells you which column to fix.*

**64. What is your single strongest contribution?**
Making the limit of the measurement a first-class part of the output, so a null result cannot be
mistaken for a clean bill of health.
*Example: turning "we found no leak" into "we found no leak, and here is the largest leak this
test could have found".*

**65. What is your weakest claim?**
Anything comparative until the second dataset is in. A quality ordering measured on one dataset
is provisional, and we say so.
*Example: if generator A beats generator B on one dataset, that could be a property of the
dataset rather than of the generator.*

### F. Technology

**66. What is it written in?**
Python 3.11 for the core and service, TypeScript and React for the browser console.
*Example: the command-line tool, the REST API and the privacy engine are all Python; only the
console is TypeScript.*

**67. Why Python?**
Because the differential-privacy libraries live there, and the workload is dominated by counting
rather than raw language speed.
*Example: rewriting in C++ would speed up the arithmetic slightly and cost us Google's
accounting library, which is a bad trade.*

**68. What are the main libraries?**
Google's `dp_accounting` for privacy arithmetic, `private-PGM` for the AIM generator, and
standard scientific Python for the rest.
*Example: NumPy and pandas do the counting; `dp_accounting` does the part that must not be
wrong.*

**69. Why not write your own privacy accounting?**
Because that is exactly where implementations fail, and they fail silently — the code runs, the
number is wrong, and nobody notices.
*Example: a subtly wrong composition rule might report epsilon 1 when the true leak is epsilon
2. Everything still works; the promise is simply false.*

**70. How do you know the accounting is right?**
We compare it against a second, independent implementation and check the two agree across many
configurations.
*Example: run the same sequence through Google's library and through an independent one. If they
disagree, something is wrong and we stop.*

**71. What database do you use?**
SQLite, for the spend ledger. It is written once per entry and single-writer, and the chain is
hash-linked with a signed head, so anything heavier would be infrastructure without a purpose.
(Not "append-only" — hash chaining alone does not detect truncation; the signed head is what
does.)
*Example: we considered PostgreSQL and rejected it — there is no concurrency requirement to
justify running a server.*

**72. Is there a user interface?**
Three, for three audiences: a command-line tool for engineers, a REST API for pipelines, and a
browser console for everyone else.
*Example: a data engineer scripts it; a hospital analyst uses the web page and never sees a
terminal.*

**73. How is it deployed?**
With Docker, so it runs identically on a laptop, a server, or inside a hospital network with no
internet access.
*Example: a hospital that will not allow data to leave the building can run the whole thing
locally.*

**74. Does it need a GPU?**
No. The generators are statistical rather than deep-learning, so a normal laptop is enough.
*Example: this is deliberate — we dropped a deep-learning generator partly because the available
hardware is a 4 GB GPU that runs out of memory.*

**75. How do you test it?**
Automated tests run on every change, including deliberately broken inputs to check that the
protections actually fire rather than merely existing.
*Example: one test feeds in a table that should be refused and fails if the tool accepts it.*

**76. What is a regression test?**
A test written for one specific bug, which fails on the old code and passes on the fixed code, so
that bug can never come back unnoticed.
*Example: we found a case where the tool returned a real value instead of a noisy one. The test
for it reproduces those exact conditions and would fail immediately if it ever returned.*

**77. How large a dataset can it handle?**
Tens of thousands of rows comfortably. Beyond that becomes an engineering question we have not
yet answered honestly.
*Example: 50,000 rows with a dozen columns is well within range. Ten million rows would need
work we have not done.*

**78. How long does a run take?**
Seconds to a few minutes at the sizes we target, depending on which generator is chosen.
*Example: the simple generator is near-instant; AIM takes longer because it spends effort
deciding which column pairs to model.*

### G. Evaluation

**79. How will you know it works?**
Four measurements: how faithful the fake data is, how useful it is, the privacy we can prove, and
the privacy an attack can actually recover.
*Example: a run that is faithful and useful but whose attack recovers a real leak has failed,
and the certificate would say so.*

**80. How do you measure usefulness?**
Train a model on the fake data, test it on real data, and compare against a model trained on real
data. The gap is the cost of privacy.
*Example: real data gives 72% accuracy, fake data gives 68%. That 4-point gap is what privacy
cost you, stated plainly.*

**81. How do you measure faithfulness?**
By comparing the relationships between columns in the fake data against the real ones.
*Example: if age and working hours are related in the real data, we check whether the same
relationship survives in the fake table, and by how much it drifted.*

**82. Which datasets, and why those?**
UCI Adult, because it is the standard benchmark and lets others compare our numbers to published
work; and ACS PUMS, which is larger and closer to real administrative data.
*Example: Adult is the "hello world" of this field. ACS is messier and bigger, so a result that
holds on both is much more believable.*

**83. Why two datasets and not one?**
Because a conclusion that only holds on one dataset is not a conclusion — it might be a property
of that dataset.
*Example: a generator that wins on Adult and loses on ACS has told you something important, and
you would never have found out with one dataset.*

**84. What result would prove you wrong?**
A stronger attacker recovering more than our stated bound; our accounting disagreeing with an
independent implementation; or our quality ordering failing to hold on the second dataset.
*Example: we wrote those three conditions down in advance. If any of them happens, we report it
rather than adjust the analysis.*

**85. How do you avoid fooling yourselves?**
Hypotheses are committed to version control before any result exists, every number carries an
uncertainty range, and every result regenerates from a fixed starting seed.
*Example: you can check the commit date on the hypothesis and see it predates the experiment.*

**86. What is a seed?**
The starting number for a random process. Fixing it makes a random run repeat exactly, so
somebody else can reproduce your result.
*Example: with seed 42 the noise added is identical every time, so two people on two machines
get the same output file.*

**87. Why report uncertainty ranges?**
Because a single number from a random process can be luck. A range shows how much of the
difference is real.
*Example: "0.031" invites belief. "0.031, somewhere between 0.013 and 0.052" tells you honestly
how much you should trust it.*

**88. What if your results come out negative?**
A negative result is still a result, provided you also state how large an effect you could have
detected. Without that, "we found nothing" is not information.
*Example: "we found no difference between groups, and we could have detected a difference of 5%
or more" is useful. "We found no difference" alone is not.*

### H. Applications

**89. Give me one concrete use case, start to finish.**
A hospital shares 50,000 diabetes records with a university lab.
*Example: the lab requests data; the hospital uploads with declared columns; we refuse the
patient-ID column and name it; they drop it and re-upload; the release goes out with a
certificate; the lab trains its model and no patient is ever exposed.*

**90. Would a hospital actually use this today?**
Not yet, and we say so plainly. It is an instrument for checking releases. Real deployment needs
budget enforcement across sessions and proper authentication.
*Example: today two separate requests could each spend the "full" budget, because the tool does
not yet remember across sessions. That must be fixed before real use.*

**91. What other sectors does this fit?**
Banking fraud data, telecom movement data, and government open data — all the same shape.
*Example: a bank wants a vendor to build a fraud detector but cannot hand over customer
transactions. Same problem, same solution.*

**92. Who would pay for this?**
The data holder, because it converts an unanswerable legal question into a signed document they
can show a regulator.
*Example: a hospital's compliance officer currently has no evidence to file. A certificate is
something they can put in a folder.*

**93. Could this be a startup?**
Possibly, though the honest positioning is a verification layer on top of existing privacy tools
rather than a replacement for them.
*Example: rather than competing with SmartNoise, the product could certify releases made using
it.*

**94. Is anyone doing exactly this already?**
Not that we found. The pieces exist separately, in two research communities that rarely cite each
other.
*Example: the privacy-theory community publishes bounds; the security community publishes
attacks. Very few papers do both, and none ship a certificate.*

**95. Does this help with DPDP or GDPR compliance?**
It provides technical evidence. Whether a regulator accepts that evidence as sufficient is a
legal question we are not qualified to answer, and we do not claim it.
*Example: we can say "this release spent 0.9 of privacy budget". We cannot say "this satisfies
Section 8", and we should not.*

**96. Could the tool be misused?**
Someone could set an enormous epsilon and still claim "differential privacy". That is exactly
why the certificate prints the odds in plain words.
*Example: at epsilon 20 the certificate would read "an attacker can identify you essentially 100
times out of 100" — which is hard to put in a marketing brochure.*

### I. Limitations

**97. What can it not do today?**
Multiple joined tables, images, free text, time series, and budgets shared across sessions.
*Example: give it a patients table and a separate visits table and it cannot handle the
relationship between them.*

**98. Why not build those too?**
Each is a substantial project on its own, and claiming all of them is the surest way to deliver
none of them.
*Example: multi-table privacy is hard because one patient appears in many rows across tables, so
the privacy cost multiplies in ways that are easy to get wrong.*

**99. Is it production-ready?**
No. Single table, one shared authentication key, no budget across sessions. We would rather state
that than oversell it.
*Example: right now everyone shares one API key, so the system cannot tell two users apart —
fine for a prototype, not for a hospital.*

**100. What is the biggest risk to the project?**
Drawing a conclusion from a single dataset. That is why the second dataset is a deliverable
rather than a stretch goal.
*Example: if we had stopped after one dataset, we might have reported a generator ordering that
does not hold in general.*

**101. What is the second biggest risk?**
Using only one attacker. A stronger one could change every measured number, which is exactly why
we print the detection limit alongside.
*Example: our attack uses a nearest-neighbour similarity score. A cleverer attack designed for
the specific generator could do better.*

**102. What if the noise makes the data useless?**
Then the honest answer is that this dataset cannot be released at that privacy level. The tool is
supposed to tell you that rather than hide it.
*Example: a dataset of 600 rows split across 50 categories may simply be too small — every count
is swamped by noise, and the certificate will show a very poor utility number.*

**103. Could somebody break your system?**
Given the signing key, yes — they could rewrite history and re-sign it. Key custody is an
organisational control and we state that openly.
*Example: if the hospital's own administrator is dishonest, no cryptography we ship will stop
them. What we prevent is an outsider altering a file undetected.*

**104. What about attacks you have not thought of?**
The formal guarantee holds against attackers nobody has imagined — that is its whole strength.
The attacked number only speaks for the attack we actually ran, which is why both appear.
*Example: a completely new attack in 2030 cannot exceed the proved bound. It could easily exceed
what our own attack found today.*

### J. Future plans

**105. What is the very next thing you would build?**
Fixing the list of columns to be measured in advance, so no generator can be scored on a question
it chose for itself.
*Example: if a generator picks which column pairs to model and we then measure exactly those
pairs, we are grading it on its own homework.*

**106. What would you do with another six months?**
A third and fourth dataset, a stronger attacker, budget enforcement across sessions, and the
shadow-model attack.
*Example: in that order, because each one removes a specific limitation we have already
identified rather than adding a new feature.*

**107. Could this become a hosted service?**
Yes, and that is the natural product form — a hospital uploads through a browser and installs
nothing.
*Example: the API and console already exist; what is missing is authentication, per-user budgets
and someone to run it.*

**108. Will you support images and text?**
Not in this project. They need entirely different generators and a separate privacy analysis.
*Example: a chest X-ray has no "columns" to count, so the whole measure-and-blur approach has to
be replaced.*

**109. What about multi-table data?**
It is a future phase, and genuinely hard, because privacy cost spreads across joins in ways that
are easy to get wrong.
*Example: one patient with 40 visits appears 40 times. Charging as though they appeared once
understates the leak by a factor of 40.*

**110. What is the certificate registry idea?**
A public place where a released dataset's privacy claim can be looked up and checked by anyone,
rather than living in an email attachment.
*Example: a researcher downloads a government dataset and checks the registry to see what
privacy budget was spent producing it.*

**111. Would you open-source it?**
That is the sensible path for a verification tool. A proof nobody is allowed to inspect is not
much of a proof.
*Example: the value of the certificate depends on people being able to check how it was
produced.*

**112. Could a regulator use this?**
That is the ambition, and it would need real engagement with one. We make no claim that it would
be accepted today.
*Example: a regulator might eventually say "a release with a certificate below epsilon 1 is
presumed compliant" — but that is their decision, not ours.*

**113. What is the research paper in this?**
Most likely the refusal gate and the detection-limit reporting, because both are general points
about how the field measures privacy rather than facts about our tool.
*Example: "attacks used to audit privacy have a detection limit that is rarely reported" is a
finding other researchers can act on.*

**114. Where does this go after the capstone?**
Either a paper on the measurement problem, or a hardened open-source tool. Both are viable, and
they are not mutually exclusive.
*Example: publish the finding, release the tool that demonstrates it.*

### K. About you and the work

**115. Have you actually built any of it?**
Yes — a working prototype runs end to end today, and we can demonstrate it live.
*Example: five commands: make a signing key, run a release, sign it, verify it, then edit one
number in the file and watch verification fail.*

**116. Can you show it running right now?**
Yes, and it runs entirely offline, so it does not depend on the room's internet.
*Example: the tamper demonstration is the memorable one — change "0.91" to "0.01" in a text
editor, re-run verify, and it prints FAILED.*

**117. Who did what on the team?**
Answer this with your real split. Name the four areas — privacy accounting and generators, the
attack and audit side, the service and console, and the evaluation — and say who owned each.
*Example: fill this in before the viva. Do not improvise it in the room, and do not claim work
that was not yours.*

**118. What was the hardest part?**
Realising that "our attack found nothing" is not a result unless you also know what the attack
could have found. That reframed the whole project.
*Example: we nearly wrote up a clean null result before checking whether our own instrument could
have detected anything at all.*

**119. What did you get wrong along the way?**
Say something true — owning a real mistake and explaining how you caught it is worth far more
than a polished answer.
*Example: at one point a component returned a real value instead of a noisy one under certain
conditions. We found it, fixed it, and wrote a test that fails on the old code.*

**120. What are you asking this panel for?**
Three specific things, so the panel has something concrete to respond to.
*Example: a hard look at the detection-limit idea, a pointer to a second public dataset with a
published schema, and guidance on whether the refusal gate stands as a contribution on its own.*

---

## 14. Cheat sheet — one page, take it in with you

**One-line pitch.** A tool that turns sensitive data into a safe fake version, and ships a
signed certificate saying exactly how private it is.

**The problem in one line.** Deleting names does not delete people — the ordinary columns
identify them anyway.

**The proof it matters.** Four fields — PIN code and a full date of birth — narrow one lakh
people down to about one.

**Epsilon in one line.** A privacy budget. Smaller is safer. At epsilon 1 an attacker who
knows everything else gets you right about 73 times in 100; a coin toss is 50.

**Our three new things.**

1. Both numbers — proved and attacked — on one release
2. We print the limit of our own attack
3. It refuses unsafe tables before reading a single value

**Four things never to say.**

- "Tamper-proof" — say tamper-**evident**
- "Nothing leaked" — say the attack found nothing above its limit, and state the limit
- "It's fake so it's safe" — that is the belief the project exists to disprove
- "We invented the privacy maths" — we use Google's library and say so

**The step that surprises people.** Building the fake table costs nothing, because once data
is private anything you calculate from it stays private.

**The step nobody else charges for.** Working out what values a column holds is a question
about real people. We charge for it.

**If you are asked something you do not know.** Say: *"I do not know, and I would rather not
guess. I can find out and come back to you."* That answer costs you nothing. Bluffing costs
you everything.

**If you lose the thread.** Go back to: *this project is about whether a privacy claim can
actually be checked, and most of what the tool does is refuse to overclaim.*

**Closing line.** "Data you can share, with the receipt attached."
