"""Generate every report number and figure from the current analysis snapshot."""
from pathlib import Path
from html import escape
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
from src.pipeline import ROOT, NOTICE, DECISIONS, SOURCE

def rule_text(r):
    return ' + '.join(r['antecedents'])+' -> '+' + '.join(r['consequents'])

def generate_report(a,root=ROOT):
    s,c=a['summary'],a['config']
    folder=root/'reports'; folder.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','figure.facecolor':'white'})
    disease=list(a['distributions']['Disease'].items())[:12]
    fig,ax=plt.subplots(figsize=(9,4.8),layout='constrained')
    ax.barh([x[0] for x in disease][::-1],[x[1] for x in disease][::-1],color='#087f8c')
    ax.set(xlabel='Retained records',title='Most represented disease labels')
    fig.savefig(folder/'disease_distribution.png',dpi=180); plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4.8),layout='constrained')
    rs=a['disease_rules']
    if rs:
        points=ax.scatter([r['support'] for r in rs],[r['confidence'] for r in rs],c=[r['lift'] for r in rs],cmap='viridis',s=45,alpha=.7)
        fig.colorbar(points,ax=ax,label='Lift')
    else: ax.text(.5,.5,'No disease rules meet these thresholds',ha='center',transform=ax.transAxes)
    ax.set(xlabel='Support',ylabel='Confidence',title='Disease-oriented rules',ylim=(0,1.05))
    fig.savefig(folder/'disease_rule_scatter.png',dpi=180); plt.close(fig)
    top=rs[:10]
    rule_table='| Rank | Antecedent | Disease consequent | Count | Support | Confidence | Lift |\n|---|---|---|---:|---:|---:|---:|\n'
    for i,r in enumerate(top,1):
        rule_table+=f"| {i} | {' + '.join(r['antecedents'])} | {r['consequents'][0]} | {r['item_count']} | {r['support']:.4f} | {r['confidence']:.4f} | {r['lift']:.4f} |\n"
    example='No disease-oriented rule meets the current thresholds.'
    if top:
        r=top[0]
        example=(f"For {rule_text(r)}, both sides occur in {r['item_count']} of {s['records']} records, so support is {r['support']:.4f}. "
                 f"The antecedent occurs in {r['antecedent_count']} records, giving confidence {r['item_count']}/{r['antecedent_count']} = {r['confidence']:.4f}. "
                 f"The consequent prevalence is {r['consequent_support']:.4f}; confidence divided by this prevalence gives lift {r['lift']:.4f}. "
                 'This is an in-sample description, not diagnostic accuracy.')
    if a.get('dataset', {}).get('id') == 'symptoms':
        sections = symptom_sections(a, rule_table, example)
    else:
        sections=[
            ('Abstract',f"This project applies Apriori association rule mining to the Disease Symptoms and Patient Profile dataset. The source has {s['raw_records']} records and {s['attributes']} attributes. After documented preprocessing, {s['records']} transactions yield {s['frequent_itemsets']} frequent itemsets, {s['association_rules']} exported association rules and {s['disease_rules']} disease-oriented rules under the current parameters. A local dashboard supports inspection, re-mining and export. {NOTICE}"),
            ('Introduction','Association rule mining identifies recurring combinations of discrete items without fitting a predictive classifier. Healthcare-themed records provide a useful academic setting for exploring symptoms and patient profiles, provided results are interpreted within the dataset.'),
            ('Problem Statement','Discover interpretable symptom/profile combinations and their associations with disease labels while preserving data provenance, handling data quality explicitly and exposing the effect of mining thresholds.'),
            ('Objectives','Audit source records; clean reproducibly; preserve meaningful item labels; mine frequent itemsets; generate and rank rules with support, confidence and lift; isolate symptom/profile-to-disease rules; provide an interactive dashboard and reproducible exports.'),
            ('Dataset Description',f"Source: {SOURCE}. Kaggle owner uom190346a, version 2, last updated 2024-01-21 according to the saved API metadata; acquired 2026-10-02. Kaggle metadata lists MIT as the license. Original filename: Disease_symptom_and_patient_profile_dataset.csv. Raw SHA-256: {s['raw_sha256']}. There are {s['disease_classes']} distinct disease labels. Age ranges from {int(next(x for x in a['quality']['columns'] if x['name']=='Age')['numeric_summary']['min'])} to {int(next(x for x in a['quality']['columns'] if x['name']=='Age')['numeric_summary']['max'])}. Four symptom fields are Fever, Cough, Fatigue and Difficulty Breathing. Other attributes are Disease, Age, Gender, Blood Pressure, Cholesterol Level and Outcome Variable. No patient identifiers or independently verified collection protocol accompany this local analysis; authentic clinical provenance and representativeness are not established."),
            ('Data Preprocessing','The workflow is raw data -> audit -> cleaning -> semantic labels -> transactions -> Boolean matrix -> Apriori -> rules -> filtering -> interpretation. The raw CSV is immutable input; every derived file is written separately.'),
            ('Data Cleaning',f"The audit detected {s['missing_values']} missing observations and {s['duplicate_records']} exact duplicates. The active policy is {a['cleaning']['duplicate_policy']}; {a['cleaning']['duplicate_rows_removed']} records were removed. {a['cleaning']['invalid_values_fixed']} invalid values were mapped to Unknown. "+' '.join(DECISIONS)),
            ('Data Labeling and Encoding','Items use Column=Value labels. Yes and No are both retained when explicitly recorded. Missing values do not mean No. Unknown values are retained in the cleaned table and omitted from mining. Age bins are inclusive 0-17, 18-30, 31-45, 46-60, and 61-120 (displayed 61+); only observed groups create items. Original ages remain in the cleaned CSV. Outcome Variable is excluded. preprocessing_metadata.json maps every observed source value to its item and rationale.'),
            ('Transaction Representation',f"One retained row forms one transaction. {s['records']} transactions encode {s['distinct_items']} observed items across nine mining fields. The disease label participates as a categorical item. Boolean matrix cells indicate membership only, not numerical severity. Different records can have identical mining transactions after outcome exclusion or age binning; these are retained because they originated from distinct full records."),
            ('Apriori Algorithm','Apriori exploits downward closure: every subset of a frequent itemset must be frequent. It discovers frequent singleton items, joins candidates level by level, prunes candidates with infrequent subsets and counts support. mlxtend.frequent_patterns.apriori runs on the Boolean matrix with an explicit maximum itemset length. This maximum limits exploration, so patterns longer than it are not evaluated.'),
            ('Association Rule Mining','Each frequent itemset is partitioned into disjoint, nonempty antecedent and consequent sets. Rules satisfying confidence and lift thresholds are kept. All rules may involve any retained items. Disease-oriented rules require exactly one Disease item on the right and no Disease item on the left. The two exported rule families are capped independently after ranking; all-rules means all qualifying rule directions within the configured search and export limits.'),
            ('Evaluation Metrics','Support(A -> B) = count(A union B) / N. Confidence(A -> B) = count(A union B) / count(A). Lift = confidence / support(B). Leverage = support(A union B) - support(A)*support(B). Conviction = (1-support(B))/(1-confidence). Lift above one indicates positive association, not statistical significance. Infinite conviction is represented as null plus conviction_infinite=true in JSON and shown as infinity in the dashboard. '+example),
            ('Experimental Setup',f"Python, pandas, NumPy, mlxtend and FastAPI provide analysis and API; React, Vite and Recharts provide the interface. Current settings: support {c['min_support']}, confidence {c['min_confidence']}, lift {c['min_lift']}, maximum itemset length {c['max_itemset_size']}, maximum exported rules per family {c['max_rules']}. At this support, a pattern needs at least {s['minimum_count']} retained records. Defaults (0.02, 0.30, 1.20, 4) balance rare disease visibility and a manageable search. These exploratory choices are not clinically validated. The UI limits support to >=0.005 and itemsets to <=5 for bounded local computation. No random sampling is used. A repeat run produces the same ordered statistics except timestamps."),
            ('Results',f"The run generated {s['frequent_itemsets']} frequent itemsets. There were {s['association_rules_before_cap']} general and {s['disease_rules_before_cap']} disease-oriented rules before independent caps; exported counts are {s['association_rules']} and {s['disease_rules']}. The dashboard labels {s['strong_rules']} exported general rules as strong using confidence >=0.70 and lift >1. This is a descriptive UI threshold, not a significance test. The run timestamp is {s['generated_at']}."),
            ('Important Association Rules',rule_table if top else 'No disease-oriented rules meet the chosen thresholds.'),
            ('Disease-Oriented Analysis',f"{len({r['consequents'][0] for r in rs})} disease labels have qualifying rules. Rare disease labels often cannot reach the support floor. An empty disease panel means no qualifying rule at the current settings, not evidence that the disease has no associations. Rules are ranked by lift, then confidence, then support, with lexical tie breaking. Closely related rules may share most antecedent items; the ranked list is not ten independent discoveries."),
            ('Dashboard','Nine sections cover overview, data quality, exploration, frequent itemsets, all association rules, disease associations, rule visualizations, Apriori parameters and reports/exports. Search and filters operate on the current mined snapshot; lowering a display filter cannot recover rules excluded during mining. Re-run Apriori to change the mining floor. Report and chart exports regenerate after a successful run.'),
            ('Discussion','High lift can result from a rare consequent and very small counts; inspect count and support alongside confidence. Profile-only rules can outrank symptom rules. Explicit No items permit absence associations, but their interpretation differs from a present symptom. Removing exact duplicates avoids overweighting repeated profiles for this academic analysis, although repeated legitimate patients cannot be ruled out. The keep-duplicates setting supports comparison.'),
            ('Limitations',NOTICE+' The dataset is small, has many rare labels, truncated names, possible aliases, unknown sampling and unverified clinical provenance. No causal identification, external validation, multiple-comparison correction, uncertainty estimation or held-out evaluation is performed. Rules are descriptive and may be redundant or unstable. The deduplication and binning choices affect support. The original outcome semantics are not inferred. This application is for local academic use and has no authentication or clinical deployment controls.'),
            ('Conclusion',f"A reproducible pipeline and dashboard were implemented for the specified first dataset. Current execution yields {s['frequent_itemsets']} frequent itemsets and {s['disease_rules']} disease-oriented rules. Interpretation remains limited to observed associations in the retained records."),
            ('Future Scope','Verify source provenance and aliases; compare deduplication and age-bin choices; examine bootstrap stability and holdout replication; add redundancy pruning and multiplicity-aware significance analysis; evaluate FP-growth for larger datasets. Any clinical application would require an independently designed and validated study.'),
            ('References',f"Dataset: {SOURCE}\n\nmlxtend Apriori documentation: https://rasbt.github.io/mlxtend/user_guide/frequent_patterns/apriori/\n\nmlxtend association rules documentation: https://rasbt.github.io/mlxtend/user_guide/frequent_patterns/association_rules/\n\nAgrawal, R. and Srikant, R. (1994). Fast Algorithms for Mining Association Rules. Proceedings of VLDB.\n\nProvided course reference: references/DMDW6_Dataset_Links_Data_and_How_to_Use.pdf.\n\nSaved source metadata: references/kaggle_metadata.json; acquisition manifest: data/raw/provenance.json.")
        ]

    md='# '+s['title']+'\n\nDMDW6 | Reproducible academic project\n\n'
    for i,(title,text) in enumerate(sections,2):
        md+=f'## {i}. {title}\n\n{text}\n\n'
        if title=='Results': md+='![Disease distribution](reports/disease_distribution.png)\n\n![Disease rule scatter](reports/disease_rule_scatter.png)\n\n'
    (root/'REPORT.md').write_text(md.rstrip()+'\n',encoding='utf-8')
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ReportTitle',fontSize=27,leading=33,textColor=colors.HexColor('#123344'),spaceAfter=22))
    styles['BodyText'].fontSize=9; styles['BodyText'].leading=14; styles['BodyText'].spaceAfter=9
    styles['Heading2'].textColor=colors.HexColor('#087f8c'); styles['Heading2'].spaceBefore=15
    small=ParagraphStyle('Small',parent=styles['BodyText'],fontSize=7,leading=10)
    story=[Paragraph('DMDW6 / RESEARCH REPORT',styles['Heading2']),Spacer(1,20),Paragraph(escape(s['title']),styles['ReportTitle']),
           Paragraph(escape(a.get('dataset', {}).get('title', 'Disease Symptoms & Patient Profile Analysis')),styles['Heading2']),Spacer(1,20)]
    kpis=[['SOURCE ROWS','RETAINED PROFILES','DISEASE RULES'],[str(s['raw_records']),str(s['records']),str(s['disease_rules'])]]
    t=Table(kpis,colWidths=[165]*3); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#e7f3f3')),('TEXTCOLOR',(0,0),(-1,-1),colors.HexColor('#123344')),('FONTSIZE',(0,1),(-1,1),22),('TOPPADDING',(0,0),(-1,-1),13),('BOTTOMPADDING',(0,0),(-1,-1),13)]))
    story.extend([t,Spacer(1,25),Paragraph(escape(NOTICE),styles['BodyText']),Paragraph(escape('Generated from this dataset’s analysis snapshot. Source acquired '+a.get('dataset', {}).get('acquired_date', '2026-10-02')+'.'),styles['BodyText']),PageBreak()])
    for i,(title,text) in enumerate(sections,2):
        story.append(Paragraph(f'{i}. {title}',styles['Heading2']))
        if title=='Important Association Rules' and top:
            rows=[[Paragraph(x,small) for x in ['Pattern -> disease','Count','Support','Confidence','Lift']]]
            for r in top: rows.append([Paragraph(escape(rule_text(r)),small),str(r['item_count']),f"{r['support']:.3f}",f"{r['confidence']:.3f}",f"{r['lift']:.2f}"])
            table=Table(rows,colWidths=[285,42,53,65,50],repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dcedef')),('VALIGN',(0,0),(-1,-1),'TOP'),('FONTSIZE',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8),('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#d8e3e6'))]))
            story.append(table)
        else:
            paragraphs=[Paragraph(escape(paragraph),styles['BodyText']) for paragraph in text.split('\n\n')]
            if title in {'Future Scope','References'}:
                heading=story.pop()
                story.append(KeepTogether([heading,*paragraphs]))
            else:
                story.extend(paragraphs)
        if title=='Results':
            for filename in ['disease_distribution.png','disease_rule_scatter.png']:
                story.append(Image(str(folder/filename),width=490,height=261))
    def footer(canvas,doc):
        canvas.saveState(); canvas.setFont('Helvetica',8); canvas.setFillColor(colors.HexColor('#607580'))
        canvas.drawString(42,25,'DMDW6 | Association mining | Academic use'); canvas.drawRightString(A4[0]-42,25,str(doc.page)); canvas.restoreState()
    SimpleDocTemplate(str(folder/'DMDW6_Report.pdf'),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=44,title=s['title'],author='DMDW6 Project').build(story,onFirstPage=footer,onLaterPages=footer)


def symptom_sections(a, rule_table, example):
    s, c, dataset = a['summary'], a['config'], a['dataset']
    coverage = len({rule['consequents'][0] for rule in a['disease_rules']})
    return [
        ('Abstract', f"Apriori discovers recorded symptom combinations in {dataset['title']}. The {s['raw_records']} source rows become {s['records']} retained symptom profiles, producing {s['frequent_itemsets']} frequent itemsets and {s['disease_rules']} disease-oriented rules across {coverage} disease labels. " + NOTICE),
        ('Dataset Description', f"Source: {dataset['source']}. Kaggle owner itachi9604, version 2. Source file: dataset.csv. Acquired {dataset['acquired_date']}. Publisher-listed license: {dataset['license']}. Raw SHA-256: {s['raw_sha256']}. The source has a Disease column and 17 symptom slots. The retained data has {s['disease_classes']} disease labels and {len(a['symptoms'])} distinct symptom types. No age, gender, blood pressure, cholesterol, or outcome fields are supplied. This educational benchmark has unverified clinical provenance; repeated rows are not independently verified patients."),
        ('Data Quality and Cleaning', f"There are {s['duplicate_records']} exact duplicate source rows. The selected policy is {a['cleaning']['duplicate_policy']}; {a['cleaning']['duplicate_rows_removed']} rows were removed. Blank symptom slots are unfilled list positions, not recorded absence and not a basis for imputing No. " + ' '.join(a['cleaning']['decisions'])),
        ('Data Labeling and Encoding', 'Every retained row contributes one transaction containing its disease and each listed symptom once. Symptoms use readable symptom_name=Yes labels. Empty slots contribute no item. A symptom not listed in the source is unobserved, not No. No demographic fields or negative symptoms are fabricated. The cleaned CSV preserves the symptom-slot structure; transactions and the Boolean matrix are separate exports.'),
        ('Apriori and Association Rules', 'Apriori uses downward closure to enumerate frequent itemsets. A rule partitions an itemset into nonempty, disjoint left and right sides. Disease-oriented rules require one Disease item on the right and none on the left. Combinations are limited to three items for this larger symptom vocabulary. This is descriptive association mining, not a trained diagnostic classifier.'),
        ('Experimental Setup', f"Support {c['min_support']}, confidence {c['min_confidence']}, lift {c['min_lift']}, maximum itemset size {c['max_itemset_size']}, and export cap {c['max_rules']} independently per rule family. At least {s['minimum_count']} retained profiles must support a combination. This dataset's defaults are 1% support, 30% confidence, lift 1.20, maximum size 3, export cap 5,000, and exact-duplicate removal. Running this source writes only its own dataset workspace."),
        ('Evaluation Metrics', 'Support is the share of retained profiles containing both sides. Confidence is the share of left-side matches also containing the right side. Lift is confidence divided by the right-side prevalence. These are sample associations, not diagnostic accuracy or statistical significance. ' + example),
        ('Results', f"Found {s['frequent_itemsets']} frequent itemsets, {s['association_rules_before_cap']} general rules, and {s['disease_rules_before_cap']} disease-oriented rules before independent export caps. Exported counts are {s['association_rules']} general rules and {s['disease_rules']} disease rules covering {coverage} of {s['disease_classes']} labels. Generated {s['generated_at']}."),
        ('Important Association Rules', rule_table if a['disease_rules'] else 'No disease-oriented rules meet these thresholds.'),
        ('Interpretation and Limits', NOTICE + ' Removing duplicates substantially reduces the benchmark. High confidence or lift can rest on very few distinct symptom profiles. Some diseases may not meet the support floor. Closely related rules are redundant, and results have no held-out clinical validation. The source overlaps heavily with other Kaggle symptom benchmarks; do not pool those copies as independent evidence.'),
        ('Dashboard and Exports', 'The dataset selector switches the displayed source. Charts, filters, tutorials, settings, and downloads follow that selection. This report covers only this dataset’s complete saved analysis; filtered CSV follows its selected rules and row limit. Original course data and reports remain in their existing workspace.'),
        ('References', f"Dataset: {dataset['source']}\n\nAttribution: itachi9604, Disease Symptom Prediction, Kaggle version 2; publisher-listed CC BY-SA 4.0. Acquisition manifest: datasets/symptoms/data/raw/provenance.json.\n\nmlxtend Apriori: https://rasbt.github.io/mlxtend/user_guide/frequent_patterns/apriori/\n\nmlxtend association rules: https://rasbt.github.io/mlxtend/user_guide/frequent_patterns/association_rules/"),
    ]
