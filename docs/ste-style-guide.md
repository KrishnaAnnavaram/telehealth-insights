# The writing standard: ASD-STE100 Simplified Technical English

Use these rules for the `README.md` of telehealth-insights and for this file. Section 3 gives the project
vocabulary. Each term in Section 3 has one meaning in all of the documentation.

## 1. The writing rules

### Words

1. Use one word for one meaning, and one meaning for one word. Do not use synonyms for variety.
2. Use a word only as one part of speech. For example, `test` is a noun or a verb, `check` is a verb.
3. Do not use phrasal verbs (`set up`, `carry out`, `find out`, `pick up`, `look up`, `come up with`).
   Use one verb: `prepare`, `do`, `find`, `get`, `make`.
4. Do not use an `-ing` form as a noun or an adjective (`the running job`, `after indexing`).
   Exception: a technical name, a file name, a command or a status value.
5. Do not use contractions (`don't`, `it's`, `can't`). Do not use slang or idioms
   (`out of the box`, `under the hood`, `at a glance`, `gotcha`, `bells and whistles`).
6. Do not use `and/or`. Write `A, B or both`.
7. Do not use `should`, `could`, `would` or `may` for instructions. Use `must` for a rule, the
   imperative for a step and `can` for a possibility.
8. Keep the articles `a`, `an` and `the` in sentences.
9. Do not make a noun cluster of more than three words. A technical name is one word.

### Sentences

1. A procedural sentence (an instruction) has a maximum of **20 words**.
2. A descriptive sentence has a maximum of **25 words**.
3. Write one instruction in one sentence.
4. Use the imperative for an instruction: `Run the tests.` Not `The tests should be run.`
5. Use the active voice. Use the passive voice only when the agent of the action is not important.
6. Use only the simple present, the simple past and the simple future.
7. Put a condition before the instruction: `If the index is stale, build it again.`
8. Do not use semicolons in sentences. Write two sentences.

### Paragraphs, notes and warnings

1. A paragraph has one topic and a maximum of **6 sentences**. Start with the topic sentence.
2. A warning or a caution starts with a clear command. Then it gives the reason.
3. A note gives information. It does not give an instruction.
4. Use a vertical list for a sequence or a set of conditions. Each item of a numbered procedure is one step.

### Tables, headings and diagrams

1. A table cell can be a short phrase. If a cell has a sentence, the sentence obeys the rules.
2. A heading is a noun phrase (`The cost model`) or an imperative (`Run the demo`).
   Do not start a heading with an `-ing` form.
3. A diagram label is a short phrase. Use the same terms as the text.

### What STE does not change

Code, commands, file names, paths, field names, environment variables, status values, enum values,
product names and URLs stay exactly as they are. They are technical names. Put them in backticks.

## 2. General words to replace

| Do not use | Use |
|---|---|
| utilize, leverage | use |
| in order to | to |
| set up | prepare, install, configure |
| carry out, perform | do |
| make sure, ensure | make sure (allowed), or `check that` |
| a lot of, lots of | many, much |
| e.g., i.e. | for example, that is |
| should (instruction) | must (rule) / imperative (step) |
| might, may (possibility) | can |
| very, really, just, simply, easily | (delete) |
| seamless, robust, powerful, blazing | (delete or give a measured fact) |

## 3. Project vocabulary

These terms have one meaning in the telehealth-insights documentation. The code names are in backticks.

### 3.1 Technical names (nouns)

| Term | Meaning | Do not use |
|---|---|---|
| **survey file** | The NEHRS physician public-use CSV, or the synthetic file with the same columns | dataset (alone), data dump |
| **codebook** | The JSON file with the role, type, codes and labels of each column | dictionary, schema, mapping |
| **missing code** | A negative code: -6, -7, -8 or -9 | skip value, sentinel |
| **skip pattern** | The survey rule that asks an item only of telemedicine users | branching, routing |
| **universe** | The physicians who get an item: all physicians or telemedicine users | population (for an item), base |
| **user** | A physician with `telemedicine = 1` | adopter, telemedicine group |
| **non-user** | A physician with `telemedicine = 0` after decoding | in-person group, control group |
| **exposure** | The `telemedicine` item | treatment, intervention |
| **outcome** | An item that the analysis compares: `telemedqual`, `telemedsat`, `timedoc` | dependent variable, result |
| **tool** | One of `telemedtool1` to `telemedtool4`. A user can name more than one | service model, modality |
| **control** | A column in the adjusted model: specialty, practice size, setting | covariate, confounder (for the column) |
| **favourable share** | The weighted share of answers in the favourable codes | top-box score, success rate |
| **weight** | The survey weight of a respondent | sampling weight (in prose), factor |
| **stratum** | A design group of the sample (`strat_p`) | layer, block |
| **PSU** | Primary sampling unit. With no PSU column, each row is one PSU | cluster (in prose) |
| **domain** | The rows that an estimate uses, for example users with an answer | subpopulation, subset |
| **adjusted model** | The weighted logistic regression with the controls | regression (alone), multivariate model |
| **primary test** | One test in the family that gets the Holm correction | main test, hypothesis |
| **sensitivity check** | The unweighted Mann-Whitney test | robustness check, secondary test |
| **report folder** | The folder with `report.md`, `results.json` and `charts/` | output, results folder |

### 3.2 Technical verbs

| Verb | Meaning |
|---|---|
| **decode** | Change raw codes to analysis values with the codebook |
| **estimate** | Calculate a weighted value with its standard error and CI |
| **adjust** | Add the controls to a model |
| **correct** | Apply the Holm step-down correction to p-values |
| **draw** | Make an SVG chart from the estimates |
