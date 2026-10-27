import React, { useRef, useState } from 'react';
import { Upload, Play, Download, RefreshCw, CheckCircle2, AlertCircle, Trash2 } from 'lucide-react';
import { Panel, Stat, Field, RuleTable, CombinationTable, Bars, MetricGuide } from './components';
import { RuleExplanation } from './HelpPages';

const stages = [
 ['validate','Validate the upload','Check the file size, CSV structure and supported columns.'],
 ['read','Read the dataset','Read source rows without replacing the saved datasets.'],
 ['audit','Audit data quality','Count missing observations and exact duplicate rows.'],
 ['clean','Clean the records','Apply duplicate handling and normalize recorded values.'],
 ['encode','Build transactions','Convert observations into readable items and a binary matrix.'],
 ['itemsets','Mine frequent itemsets','Apriori finds combinations meeting minimum support.'],
 ['results','Generate association rules','Calculate confidence and lift, then rank the results.'],
];

function Preview({ rows }) {
 if (!rows?.length) return null;
 const columns = Object.keys(rows[0]);
 return <div className="table-wrap demo-preview"><table><thead><tr>{columns.map(c=><th key={c}>{c}</th>)}</tr></thead><tbody>{rows.map((row,i)=><tr key={i}>{columns.map(c=><td key={c}>{Array.isArray(row[c])?row[c].join(' + '):String(row[c]??'')}</td>)}</tr>)}</tbody></table></div>;
}

function saveFile(name, text, type='text/csv') {
 const url = URL.createObjectURL(new Blob([text], {type}));
 const link = document.createElement('a'); link.href=url; link.download=name;
 document.body.append(link); link.click(); link.remove(); setTimeout(()=>URL.revokeObjectURL(url),1000);
}

export default function UploadDemo({ session, setSession }) {
 const { file, events=[], result=null, error='', busy=false } = session;
 const input = useRef(null);
 const [support,setSupport]=useState(5),[confidence,setConfidence]=useState(30),[lift,setLift]=useState(1.2),[dedupe,setDedupe]=useState(true);
 const [family,setFamily]=useState('disease_rules');
 const update=patch=>setSession(current=>({...current,...patch}));
 const chooseFile=selected=>{
  if(!selected)return;
  if(!selected.name.toLowerCase().endsWith('.csv')||selected.size>1_000_000){update({file:null,result:null,events:[],error:'Choose a .csv file smaller than 1 MB.'});return}
  update({file:selected,events:[],result:null,error:''});
 };
 const run=async event=>{
  event.preventDefault(); if(!file||busy)return;
  update({busy:true,error:'',events:[],result:null});
  let complete=false;
  try {
   const params=new URLSearchParams({min_support:support/100,min_confidence:confidence/100,min_lift:lift,remove_duplicates:dedupe});
   const response=await fetch(`/api/demo/analyze?${params}`,{method:'POST',headers:{'Content-Type':'text/csv'},body:file});
   if(!response.ok){const payload=await response.json();throw Error(typeof payload.detail==='string'?payload.detail:JSON.stringify(payload.detail))}
   const reader=response.body.getReader(),decoder=new TextDecoder(); let pending='';
   const receive=line=>{
    if(!line.trim())return;
    const event=JSON.parse(line);
    if(event.type==='error')throw Error(event.message);
    if(event.type==='step')setSession(current=>({...current,events:[...current.events,event]}));
    if(event.type==='complete'){complete=true;update({result:event})}
   };
   try {
    while(true){const {value,done}=await reader.read();pending+=decoder.decode(value,{stream:!done});const lines=pending.split('\n');pending=lines.pop();lines.forEach(receive);if(done)break}
    receive(pending);
   } finally {reader.releaseLock()}
   if(!complete)throw Error('The connection ended before results arrived. Run the demo again.');
  } catch(e){update({error:e.message})}
  finally{update({busy:false})}
 };
 const clear=()=>{setSession({events:[]});if(input.current)input.current.value=''};
 const a=result?.analysis,s=a?.summary;
 const active=busy?events.length:-1;
 return <>
 <div className="info-strip"><Upload size={22}/><p><b>Your file. The real Apriori pipeline.</b> Watch every stage, inspect intermediate data and explain the final rules. Uploads are deleted from the server after each run; results stay in this tab until you clear or refresh it.</p></div>
 <div className="grid-two demo-setup">
  <Panel title="1. Bring a dataset" subtitle="CSV · UTF-8 · up to 1 MB / 1,000 records">
   <div className="demo-drop" onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();if(!busy)chooseFile(e.dataTransfer.files[0])}}>
    <Upload size={30}/><label htmlFor="demo-file">Choose a CSV or drop it here</label>
    <input ref={input} id="demo-file" type="file" accept=".csv,text/csv" disabled={busy} onChange={e=>chooseFile(e.target.files[0])}/>
    {file&&<p><b>{file.name}</b> · {(file.size/1024).toFixed(1)} KB</p>}
   </div>
   <p className="muted demo-copy">Use patient-profile columns or Disease + Symptom_1 through Symptom_17. Start with either ready-made synthetic sample:</p>
   <div className="demo-actions"><a className="secondary" download href="/api/demo/sample/profiles"><Download size={16}/> Patient profiles</a><a className="secondary" download href="/api/demo/sample/symptoms"><Download size={16}/> Symptom list</a></div>
   <p className="muted demo-copy">Each sample has 63 rows, three fictional disease groups and three exact duplicates. The profile sample includes an invalid age and an empty value to demonstrate cleaning. These are invented presentation examples.</p>
  </Panel>
  <Panel title="2. Run the model" subtitle="This run uses only your uploaded CSV.">
   <form onSubmit={run}><fieldset className="parameter-fields" disabled={busy}><div className="parameters">
    <Field label="Minimum support (%)"><input type="number" min="5" max="100" step="1" required value={support} onChange={e=>setSupport(e.target.value)}/></Field>
    <Field label="Minimum confidence (%)"><input type="number" min="0" max="100" step="1" required value={confidence} onChange={e=>setConfidence(e.target.value)}/></Field>
    <Field label="Minimum lift"><input type="number" min="0" max="1000" step="0.1" required value={lift} onChange={e=>setLift(e.target.value)}/></Field>
    <Field label="Duplicate handling"><select value={String(dedupe)} onChange={e=>setDedupe(e.target.value==='true')}><option value="true">Remove exact duplicates</option><option value="false">Keep every row</option></select></Field>
   </div></fieldset><p className="muted">Combinations up to 3 items; up to 5,000 exported rules per family. Steps below update as the server completes them.</p>
   <div className="form-footer"><button className="primary" disabled={!file||busy} type="submit">{busy?<RefreshCw size={17} className="spin"/>:<Play size={17}/>} {busy?'Processing upload…':result?'Run again':'Run live analysis'}</button><button type="button" className="secondary" disabled={busy||(!file&&!events.length)} onClick={clear}><Trash2 size={16}/> Clear demo</button></div></form>
  </Panel>
 </div>
 {error&&<div role="alert" className="error"><AlertCircle size={18}/>{error}</div>}
 <Panel title="3. Follow the processing steps" subtitle="Expand completed stages to inspect actual intermediate values. Fast stages may arrive together.">
  <div className="demo-progress" role="progressbar" aria-label="Completed analysis stages" aria-valuenow={events.length} aria-valuemin={0} aria-valuemax={stages.length}><span style={{width:`${events.length/stages.length*100}%`}}/></div>
  <p className="muted" role="status" aria-live="polite">{busy?`Processing · ${events.length} of ${stages.length} stages complete`:result?'Analysis complete · temporary server files removed':error?'Run stopped · review the error and retry':'Ready when you are'}</p>
  <ol className="demo-timeline">{stages.map(([id,title,description],i)=>{
   const event=events.find(e=>e.step===id),current=active===i;
   return <li key={id} className={event?'done':current?'current':''}><span className="demo-step-icon">{event?<CheckCircle2 size={20}/>:current?<RefreshCw size={19} className="spin"/>:i+1}</span><div><h3>{title}{current&&' · running'}</h3><p>{event?.message||description}</p>{event&&(event.preview||event.transactions)&&<details><summary>Inspect {id==='encode'?'transactions and binary encoding':'first five records'}</summary>{event.preview&&<Preview rows={event.preview}/>} {event.transactions&&<><p className="muted">Each transaction contains the recorded items from one retained row.</p><ol className="demo-transactions">{event.transactions.map((t,i)=><li key={i}>{t.join(' · ')}</li>)}</ol><p className="muted">Binary matrix preview · first 5 records and up to 12 item columns. 1 = item present, 0 = not in this transaction.</p><Preview rows={event.matrix}/></>}</details>}</div></li>
  })}</ol>
 </Panel>
 {result&&<div className="demo-results">
  <Panel title={`4. Results from ${file?.name}`} subtitle="All metrics below are calculated from this upload. The saved datasets are unchanged."><div className="stats-grid"><Stat label="Retained records" value={s.records} detail={`${s.raw_records} uploaded; ${a.cleaning.duplicate_rows_removed} duplicates removed`}/><Stat label="Distinct items" value={s.distinct_items} detail="Columns in the binary matrix"/><Stat label="Frequent itemsets" value={s.frequent_itemsets} detail={`Minimum count: ${s.minimum_count}`}/><Stat label="Disease associations" value={s.disease_rules} detail={`${s.association_rules} total rules`} accent/></div></Panel>
  <div className="grid-two"><Panel title="Uploaded disease distribution"><Bars data={Object.entries(a.distributions.Disease).map(([name,value])=>({name,value}))}/></Panel><Panel title="Explain a discovered association">{a.disease_rules.length?<RuleExplanation rule={a.disease_rules[0]} records={s.records}/>:<p className="muted">No disease rules meet these thresholds. Lower confidence or lift and run again.</p>}</Panel></div>
  <Panel title="Inspect the association rules" subtitle={`Showing the first 50 ranked rules in this family. Download the full results below.`} action={<div className="segmented"><button className={family==='disease_rules'?'selected':''} onClick={()=>setFamily('disease_rules')}>Disease rules</button><button className={family==='rules'?'selected':''} onClick={()=>setFamily('rules')}>All rules</button></div>}><RuleTable rules={a[family].slice(0,50)}/></Panel>
  <Panel title="Frequent itemsets" subtitle="First 25 combinations ordered by support"><CombinationTable rows={a.itemsets.slice(0,25)}/></Panel>
  <Panel title="Download this run" subtitle="Save the results you need before clearing or refreshing this tab."><div className="demo-actions">{Object.entries(result.artifacts).map(([key,text])=><button className="secondary" key={key} onClick={()=>saveFile(`upload_${key}.csv`,text)}><Download size={16}/>{key.replaceAll('-',' ')} CSV</button>)}<button className="secondary" onClick={()=>saveFile('upload_analysis.json',JSON.stringify(a,null,2),'application/json')}><Download size={16}/> Analysis JSON</button></div></Panel><MetricGuide/>
 </div>}
 </>;
}
