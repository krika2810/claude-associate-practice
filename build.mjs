import fs from 'fs';

const domains = [
  [1,'Prompting and Task Execution',14],
  [2,'Output Evaluation and Validation',21],
  [3,'Product and Model Selection',12],
  [4,'Workflow Integration and Solution Design',16],
  [5,'Configuration and Knowledge Management',12],
  [6,'Governance, Risk, and Responsible Use',15],
  [7,'Troubleshooting and Optimization',10],
];
const counts=[8,13,7,10,7,9,6];
const letters=['A','B','C','D'];
let id=0;
const q=(set,domain,stem,options,correct,why,multi=false)=>({id:++id,set,domain,stem,options,correct:Array.isArray(correct)?correct:[correct],why,multi});
const roleCases=[
 ['operations lead','turn weekly incident notes into a clear leadership update','audience, decision needed, source notes, and required format'],
 ['marketing manager','draft a launch brief from approved product facts','audience, approved claims, tone, and output structure'],
 ['project manager','compare three delivery plans','decision criteria, constraints, evidence, and a comparison table'],
 ['HR partner','summarize employee survey themes','scope, anonymized source data, audience, and categories'],
 ['teacher','create a lesson plan from a curriculum excerpt','learner level, objectives, source excerpt, and lesson format'],
 ['sales operations analyst','identify causes of pipeline slippage','definitions, clean input data, comparison period, and output schema'],
 ['communications lead','adapt a technical memo for executives','target audience, decisions required, source memo, and length'],
 ['customer success manager','prepare renewal-risk summaries','risk criteria, account evidence, desired format, and escalation rule'],
 ['procurement analyst','compare vendor proposals','weighted criteria, proposal text, mandatory requirements, and assumptions'],
 ['program manager','turn meeting notes into an action register','owner/date rules, source notes, and a structured table'],
 ['research coordinator','synthesize interviews into themes','research question, transcripts, coding criteria, and evidence quotes'],
 ['finance business partner','explain budget variance to department heads','verified figures, comparison baseline, audience, and required caveats'],
 ['support lead','draft replies to common low-risk questions','approved knowledge, response policy, tone, and escalation conditions'],
 ['policy analyst','summarize a newly issued policy','official source, affected audience, effective date, and citation requirement'],
];
const riskyCases=[
 ['a regulation summary with a subsection citation','the official regulation text'],
 ['a board memo containing quarterly revenue figures','the signed finance report'],
 ['a medical-information handout','approved clinical guidance and expert review'],
 ['a hiring summary that ranks candidates','job criteria, source applications, and human review'],
 ['a market report quoting competitor prices','current first-party pricing pages'],
 ['a contract summary stating termination dates','the executed agreement'],
 ['a customer incident report naming root cause','system logs and the incident owner'],
 ['a policy answer describing employee benefits','the current approved policy'],
 ['an executive brief quoting survey percentages','the cleaned survey dataset'],
 ['a research note citing academic papers','the original papers'],
 ['a press response containing product claims','the approved claims library and communications owner'],
 ['a tax-process guide','current tax authority guidance and a qualified reviewer'],
 ['a supplier assessment describing certifications','current certification records'],
 ['a project status note claiming a milestone is complete','the delivery tracker and accountable owner'],
 ['a translation of a safety procedure','the source procedure and a fluent domain reviewer'],
 ['a customer churn analysis','the governed analytics dataset and metric definitions'],
];
const sensitive=[
 ['customer names and account numbers','remove or anonymize identifiers under policy before analysis'],
 ['employee health information','use only the approved protected-data workflow and authorized access'],
 ['unreleased financial results','do not upload them unless the approved environment and policy explicitly permit it'],
 ['student records with grades and IDs','de-identify the records and follow education-data policy'],
 ['support tickets containing passwords','remove the secrets and rotate exposed credentials before any analysis'],
 ['legal matter notes under privilege','confirm the approved tool, access controls, and legal policy first'],
 ['biometric access logs','apply privacy, retention, and purpose-limitation requirements'],
 ['customer call transcripts','remove unnecessary personal data and confirm consent and retention rules'],
 ['candidate applications','limit access, use job-related criteria, and require human decision ownership'],
 ['source code containing API keys','remove and rotate the keys; use a secret store'],
 ['cross-border customer records','check data-location and transfer requirements before use'],
 ['children’s personal information','do not proceed without the specifically approved safeguarded process'],
];
const modelCases=[
 ['thousands of short FAQ drafts','speed and low cost matter; the task is straightforward','Haiku'],
 ['a nuanced strategy memo with difficult trade-offs','deep reasoning and quality matter more than latency','Opus'],
 ['routine analysis with solid quality at balanced cost','quality, speed, and cost all matter','Sonnet'],
 ['rapid classification of simple feedback labels','high throughput and consistency matter','Haiku'],
 ['complex cross-document reasoning for an executive decision','maximum reasoning quality matters','Opus'],
 ['drafting and revising a detailed project plan','balanced reasoning and speed matter','Sonnet'],
 ['high-volume extraction of fixed fields from clean text','the schema is simple and throughput matters','Haiku'],
 ['evaluating several ambiguous organizational designs','subtle trade-offs and deep analysis matter','Opus'],
 ['creating polished first drafts of standard business content','good quality and responsive iteration matter','Sonnet'],
 ['screening a large set of messages for a simple routing rule','cost and latency dominate','Haiku'],
];
const workflowCases=[
 ['weekly status reporting','collect updates, validate facts, draft the report, then have the owner approve it'],
 ['proposal development','clarify requirements, research evidence, draft sections, review claims, then finalize'],
 ['meeting follow-up','extract actions, verify owners and dates, publish after the meeting owner reviews'],
 ['customer feedback analysis','clean data, define categories, classify, sample-check, synthesize, then decide actions'],
 ['policy Q&A','retrieve approved policy, draft a cited answer, verify currency, then escalate exceptions'],
 ['campaign planning','define objective and audience, generate options, assess constraints, choose, then measure'],
 ['vendor comparison','set criteria, normalize evidence, flag gaps, compare, then retain human selection'],
 ['incident communication','confirm facts, tailor by audience, obtain incident-owner approval, then distribute'],
 ['training design','define outcomes, build material from approved sources, pilot, collect feedback, then revise'],
 ['research synthesis','frame the question, gather sources, assess source quality, synthesize, then review'],
 ['onboarding documentation','map tasks, retrieve current procedures, draft, validate with owners, then publish'],
 ['renewal-risk review','define risk signals, collect account evidence, generate summaries, have account owners verify'],
];
const configCases=[
 ['brand-content Project','brand voice, approved terminology, forbidden claims, audience rules, and current brand files'],
 ['HR policy Project','answer only from approved policy sources, cite the source, and escalate uncovered cases'],
 ['proposal Project','required structure, qualification rules, approved case studies, and current service descriptions'],
 ['support Project','approved knowledge, reply style, troubleshooting order, and escalation conditions'],
 ['research Project','source-quality rules, citation format, date checks, and a standard evidence table'],
 ['training Project','learner level, learning objectives, approved curriculum, and accessibility rules'],
 ['operations Project','metric definitions, reporting cadence, source-of-truth links, and exception rules'],
 ['communications Project','audience profiles, tone, approval path, current message house, and prohibited claims'],
 ['procurement Project','evaluation criteria, mandatory terms, current vendor material, and conflict rules'],
 ['project-delivery Project','status definitions, templates, decision log, current plan, and escalation thresholds'],
];
const troubleCases=[
 ['answers are polished but omit required risks','add an explicit completeness checklist and require a risk section'],
 ['outputs vary in headings every run','provide a fixed schema and a good example'],
 ['Claude uses an outdated policy','replace the stale knowledge source and identify the current source in instructions'],
 ['a long chat starts contradicting earlier decisions','summarize durable decisions and restart with clean context'],
 ['responses are too generic','supply concrete context, audience, constraints, and success criteria'],
 ['a workflow is slow and expensive for simple tasks','test a smaller model on a representative evaluation set'],
 ['summaries invent missing values','tell Claude to mark missing data explicitly and verify against source rows'],
 ['a Project ignores important instructions','shorten, prioritize, and remove conflicting instructions'],
 ['classification accuracy drops on unusual cases','add representative edge cases and a human-review threshold'],
 ['research outputs cite low-quality pages','define source hierarchy and require primary-source verification'],
 ['the same prompt fails only on oversized documents','split the material, preserve metadata, and synthesize in stages'],
 ['users accept drafts without checking them','add a review gate and evidence checklist before use'],
];

function makeSet(set){
 let a=[];
 // Domain 1, 8
 for(let i=0;i<8;i++){
  let [role,task,need]=roleCases[(set-1)*6+i];
  if(i%4===3){a.push(q(set,1,`A ${role} must ${task}. Which THREE prompt elements most directly improve the first response?`,[need.split(', ')[0],need.split(', ')[1],need.split(', ').slice(2).join(', '),'A request that Claude "be brilliant"','An instruction to hide uncertainty'],[0,1,2],`Strong prompts make the task, evidence, constraints, audience, and output explicit. Vague praise and hiding uncertainty do not add usable direction.`,true));}
  else if(i%3===1){a.push(q(set,1,`A ${role} asks Claude to ${task}, but the request is too large for one reliable pass. What is the best next step?`,['Ask for the final answer again with more urgency',`Break the work into stages, define the output of each stage, and validate before continuing`,'Remove all context to make the prompt shorter','Ask Claude to choose unstated business priorities'],1,`Task decomposition reduces hidden assumptions and creates review points. The other choices either repeat the same failure or discard information needed for the task.`));}
  else {a.push(q(set,1,`Which prompt is best for a ${role} who needs to ${task}?`,[`"${task}."`,`"Act as an expert and make it perfect."`,`"Using the attached approved material, ${task}. Include ${need}. Mark missing evidence instead of guessing."`,'"Think step by step and do whatever you think is best."'],2,`The strongest option supplies grounded inputs, task context, success conditions, and a rule for missing evidence. A persona or generic request cannot replace those details.`));}
 }
 // Domain 2, 13
 for(let i=0;i<13;i++){
  let [out,src]=riskyCases[(set-1)*3+i];
  if(i%5===2){a.push(q(set,2,`Claude produces ${out}. Which THREE checks should happen before it is used?`,[`Compare material claims with ${src}`,'Check that the output covers the requested scope','Check tone and format for the intended audience','Accept every citation because it looks specific','Use Claude’s confidence statement as proof'],[0,1,2],`Validation covers factual support, completeness, and fitness for the audience. Specific-looking citations and self-reported confidence are not evidence.`,true));}
  else if(i%4===1){a.push(q(set,2,`Two Claude drafts of ${out} differ. What is the most reliable way to select between them?`,['Choose the longer draft','Choose the draft with the strongest tone',`Score both against the same criteria and verify disputed claims using ${src}`,'Ask Claude which draft it prefers and accept that answer'],2,`A shared rubric plus external verification makes the comparison repeatable and evidence-based. Length, tone, or model preference do not establish correctness.`));}
  else if(i%4===3){a.push(q(set,2,`Claude cannot find a value needed for ${out}. What should the associate prefer?`,['A plausible estimate with no label','A confident sentence that avoids the gap','An explicit "not found in the provided sources" marker and a request for the missing evidence','A fabricated citation that can be checked later'],2,`Clearly surfacing missing evidence preserves traceability and invites the right follow-up. Guessing turns an information gap into a hidden error.`));}
  else {a.push(q(set,2,`Claude returns ${out} confidently. What is the most appropriate next action?`,['Share it because fluent language indicates reliability',`Verify the important claims against ${src} and obtain the needed human review`,'Only ask Claude to rewrite it in a cautious tone','Delete it and avoid using Claude for the task'],1,`Fluency is not accuracy. The right response is proportionate verification and human review, not blind acceptance or abandoning a useful workflow.`));}
 }
 // Domain 3, 7
 for(let i=0;i<7;i++){
  let [task,trade,model]=modelCases[(set-1)*3+i];
  if(i===5){a.push(q(set,3,'A conversation has accumulated many outdated drafts and Claude is mixing old and new decisions. Which TWO actions best restore reliable context?',['Continue in the same thread and repeat the latest instruction','Create a concise handoff of current facts and decisions','Start a new conversation using that handoff','Upload more unrelated background'],[1,2],'A clean restart plus a standalone summary removes stale context while preserving current decisions. Repetition in a polluted thread and unrelated material add noise.',true));}
  else if(i===6){a.push(q(set,3,'Which product feature is the best home for recurring work that needs stable instructions and a maintained set of reference files?',['A fresh temporary chat for every task','A Claude Project','An image artifact','A model switch without instructions'],1,'A Project keeps task-specific instructions and knowledge together across related work. A model choice or artifact does not manage recurring context.'));}
  else {a.push(q(set,3,`A team needs ${task}; ${trade}. Which model family is the best starting point?`,['Haiku','Sonnet','Opus','The largest model in every case'],['Haiku','Sonnet','Opus'].indexOf(model),`${model} is the best starting fit for this trade-off. Model selection should match complexity, latency, quality, and cost, then be tested on representative work.`));}
 }
 // Domain 4, 10
 for(let i=0;i<10;i++){
  let [name,flow]=workflowCases[(set-1)*2+i];
  if(i%5===4){a.push(q(set,4,`A team is redesigning ${name}. Which THREE design choices best support a dependable workflow?`,['Define the business outcome and success measure','Place verification or approval where errors matter','Assign owners for inputs, exceptions, and final decisions','Automate every decision immediately','Hide limitations from stakeholders'],[0,1,2],`A dependable workflow starts with the outcome, adds controls at risk points, and preserves ownership. Automation scope should follow evidence, and limits should be communicated.`,true));}
  else if(i%3===1){a.push(q(set,4,`Which sequence is the strongest design for ${name}?`,[flow,'Generate a final output first, then look for requirements','Automate the current process unchanged and measure nothing','Let Claude choose sources, policy, and approval rules'],0,`The best sequence decomposes the workflow, grounds it in inputs, and includes validation or ownership. Claude supports the work; it does not inherit governance or business authority.`));}
  else {a.push(q(set,4,`Before adding Claude to ${name}, what should the associate do first?`,['Pick the most expensive model','Map the current goal, inputs, decisions, pain points, risks, and owners','Promise stakeholders that the workflow will be fully autonomous','Remove all human review'],1,`Workflow design starts with the business process and its failure modes. Product and automation choices follow from that analysis.`));}
 }
 // Domain 5, 7
 for(let i=0;i<7;i++){
  let [name,items]=configCases[(set-1)*3+i];
  if(i%4===2){a.push(q(set,5,`Which THREE maintenance actions keep a ${name} trustworthy?`,['Assign an owner to review instructions and sources','Remove or replace superseded files','Test representative tasks after changes','Keep conflicting versions so Claude can decide','Treat connectors as permanently current without checks'],[0,1,2],`Configurations need ownership, source hygiene, and regression checks. Conflicting sources and assumed freshness create silent failure.`,true));}
  else if(i%3===1){a.push(q(set,5,`The ${name} gives inconsistent answers after several contributors added instructions. What is the best fix?`,['Add more instructions without reading the old ones','Consolidate conflicts, prioritize rules, keep them concise, and test common tasks','Switch models and leave the conflicts in place','Tell users to ignore inconsistent answers'],1,`System-level instructions should be clear, ordered, and maintainable. Model changes do not repair contradictory configuration.`));}
  else {a.push(q(set,5,`What belongs in the initial configuration for a ${name}?`,[items,'Every file the team can access, whether relevant or not','Only a one-line instruction to be helpful','Unverified web content copied without dates or owners'],0,`The best configuration contains task-relevant rules and authoritative, maintained knowledge. More context is not automatically better.`));}
 }
 // Domain 6, 9
 for(let i=0;i<9;i++){
  let [data,action]=sensitive[(set-1)*3+i];
  if(i%4===1){a.push(q(set,6,`A team wants to use ${data} with Claude. Which THREE questions must be answered first?`,['Does policy permit this data in the chosen environment?','Can the data be minimized, redacted, or anonymized?','Who is accountable for access and review?','Will a more confident prompt remove the privacy risk?','Can the policy be skipped because the use is internal?'],[0,1,2],`Data use depends on policy, minimization, access, and accountability. Prompt wording and internal intent do not override privacy or regulatory controls.`,true));}
  else if(i%3===2){a.push(q(set,6,`Which action best preserves responsible human ownership when Claude is used with ${data}?`,['Let Claude make the final high-impact decision','Assign a qualified human to review evidence, exceptions, and the final decision','Accept the output if most sentences look reasonable','Remove the audit trail to reduce storage'],1,`High-impact or sensitive decisions need qualified human ownership and an auditable review path. Statistical plausibility is not individual correctness.`));}
  else {a.push(q(set,6,`An associate is asked to analyze ${data}. What is the most appropriate response?`,[action,'Upload it first and check policy later','Tell Claude that the data is confidential and proceed','Move it to a personal account to avoid organizational restrictions'],0,`Responsible use follows the organization’s data rules before processing. A label inside a prompt or a different account is not a security control.`));}
 }
 // Domain 7, 6
 for(let i=0;i<6;i++){
  let [symptom,fix]=troubleCases[(set-1)*3+i];
  if(i===4){a.push(q(set,7,`A workflow improves after one prompt edit. Which TWO steps best show the improvement is real?`,['Run the old and new versions on the same representative cases','Measure against predefined quality and efficiency criteria','Judge from one unusually good output','Change the model, prompt, and data simultaneously'],[0,1],'A controlled comparison on representative work isolates the change and uses repeatable measures. One anecdote or many simultaneous changes cannot establish cause.',true));}
  else {a.push(q(set,7,`A team reports that ${symptom}. What is the best first correction?`,[fix,'Repeat the same prompt in capital letters','Always move to the largest model before diagnosis','Add unrelated context to make the prompt longer'],0,`The correction targets the likely failure source and can be tested. Urgency, model size, and extra context are not substitutes for diagnosis.`));}
 }
 return a;
}
const questions=[...makeSet(1),...makeSet(2)];
if(questions.length!==120) throw new Error(`Expected 120, got ${questions.length}`);
for(const set of [1,2]) for(const [d,,] of domains){const n=questions.filter(x=>x.set===set&&x.domain===d).length;if(n!==counts[d-1])throw new Error(`${set}/${d}: ${n}`)}
const payload=JSON.stringify({domains,questions});
const css=fs.readFileSync('style.css','utf8');
const js=fs.readFileSync('app.js','utf8');
const html=`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#07100d"><title>Claude Associate Practice Lab</title><meta name="description" content="Two original 60-question practice sets for the Claude Certified Associate – Foundations exam."><style>${css}</style></head><body><header><a class="brand" href="#">Claude Associate <b>Practice Lab</b></a><button id="theme" aria-label="Toggle theme">◐</button></header><main id="app"></main><footer>Original practice questions aligned to the official CCAO-F v1.0 blueprint. Not affiliated with or endorsed by Anthropic.</footer><script>window.BANK=${payload};${js}</script></body></html>`;
fs.writeFileSync('index.html',html);
