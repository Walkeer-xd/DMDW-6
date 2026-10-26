import React from 'react';
import { X, SlidersHorizontal } from 'lucide-react';
import { Panel, Field, ChoiceField, displayItem, readable, pct, num } from './components';

const supportOptions=[[0,'Any frequency'],[.005,'At least 0.5%'],[.01,'At least 1%'],[.02,'At least 2%'],[.05,'At least 5%'],[.1,'At least 10%'],[.25,'At least 25%'],[.5,'At least 50%'],[1,'100%']];
const rowOptions=[[25,'25 patterns'],[50,'50 patterns'],[100,'100 patterns'],[250,'250 patterns'],[500,'500 patterns'],[1000,'1,000 patterns'],[100000,'All matching patterns']];
const lengthOptions=[[5,'Any length'],[1,'1 condition'],[2,'Up to 2 conditions'],[3,'Up to 3 conditions'],[4,'Up to 4 conditions']];

export function ItemSelect({data,value,onChange,label='Contains a condition',includeDiseases=false}) {
 const groups={};
 data.itemsets.filter(row=>row.length===1).forEach(row=>{
  const item=row.itemset[0],group=item.split('=')[0];
  if(!includeDiseases&&group==='Disease')return;
  (groups[group]??=[]).push(item);
 });
 return <Field label={label}><select value={value} onChange={event=>onChange(event.target.value)}><option value="">Any condition</option>{Object.entries(groups).sort(([a],[b])=>a.localeCompare(b)).map(([group,items])=><optgroup key={group} label={readable(group)}>{items.sort().map(item=><option key={item} value={item}>{displayItem(item)}</option>)}</optgroup>)}</select></Field>;
}

export function PatternFilters({data,filter,update,disease,onDisease,sort,onSort,onReset}) {
 const chips=[];
 if(disease)chips.push([disease,()=>onDisease('')]);
 if(filter.item)chips.push([displayItem(filter.item),()=>update('item','')]);
 if(filter.symptom)chips.push([readable(filter.symptom),()=>update('symptom','')]);
 if(filter.min_support)chips.push([`Support ≥ ${pct(filter.min_support)}`,()=>update('min_support',0)]);
 if(filter.min_confidence)chips.push([`Confidence ≥ ${pct(filter.min_confidence)}`,()=>update('min_confidence',0)]);
 if(filter.min_lift)chips.push([`Lift ≥ ${filter.min_lift}×`,()=>update('min_lift',0)]);
 if(filter.max_antecedent_length<5)chips.push([`Up to ${filter.max_antecedent_length} conditions`,()=>update('max_antecedent_length',5)]);
 return <Panel title="Find a pattern" subtitle={`Display filters use the saved analysis. Its mining support floor is ${pct(data.config.min_support)}; change Analysis settings to discover rarer patterns.`} action={<button className="text-button" onClick={onReset}>Reset filters</button>}><div className="filters"><ChoiceField label="Disease on the right" value={disease} onChange={onDisease} options={[["","All diseases"],...Object.keys(data.distributions.Disease).sort().map(name=>[name,name])]}/><ItemSelect data={data} value={filter.item} onChange={value=>update('item',value)}/><ChoiceField label="Sort by" value={sort} onChange={onSort} options={[["lift","Lift"],["confidence","Confidence"],["support","Frequency"],["item_count","Supporting profiles"]]}/></div><details className="advanced-controls"><summary><SlidersHorizontal size={14}/> More filters</summary><div className="filters advanced-selects"><ChoiceField label="Minimum support" value={filter.min_support} onChange={value=>update('min_support',Number(value))} options={supportOptions}/><ChoiceField label="Minimum confidence" value={filter.min_confidence} onChange={value=>update('min_confidence',Number(value))} options={[[0,'Any confidence'],[.3,'At least 30%'],[.5,'At least 50%'],[.7,'At least 70%'],[.8,'At least 80%'],[.9,'At least 90%'],[1,'100%']]}/><ChoiceField label="Minimum lift" value={filter.min_lift} onChange={value=>update('min_lift',Number(value))} options={[[0,'Any lift'],...[1,1.2,2,3,5,10,20,50].map(value=>[value,`At least ${value}×`])]}/><ChoiceField label="Maximum conditions" value={filter.max_antecedent_length} onChange={value=>update('max_antecedent_length',Number(value))} options={lengthOptions}/><ChoiceField label="Rows to show" value={filter.top_n} onChange={value=>update('top_n',Number(value))} options={rowOptions}/><ChoiceField label="Symptom on the left" value={filter.symptom} onChange={value=>update('symptom',value)} options={[["","Any symptom"],...data.symptoms.map(name=>[name,readable(name)])]}/></div></details>{chips.length>0&&<div className="filter-chips" aria-label="Active filters">{chips.map(([label,clear])=><button key={label} onClick={clear} aria-label={`Remove filter: ${label}`}>{label}<X size={12}/></button>)}</div>}</Panel>;
}

export function CombinationFilters({data,item,setItem,support,setSupport,size,setSize,limit,setLimit}) {
 return <Panel title="Find a combination" subtitle={`Saved mining support floor: ${pct(data.config.min_support)}. Display filters narrow the existing combinations.`}><div className="filters compact"><ItemSelect data={data} value={item} onChange={setItem} label="Contains an item" includeDiseases/><ChoiceField label="Minimum support" value={support} onChange={value=>setSupport(Number(value))} options={supportOptions}/><ChoiceField label="Combination size" value={size} onChange={value=>setSize(Number(value))} options={lengthOptions.map(([value,text])=>[value,text.replace('condition','item')])}/><ChoiceField label="Rows to show" value={limit} onChange={value=>setLimit(Number(value))} options={rowOptions}/></div></Panel>;
}
