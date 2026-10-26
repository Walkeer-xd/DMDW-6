import React, { useEffect, useId, useState } from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ScatterChart, Scatter, ZAxis, Cell } from 'recharts';
import { ArrowRight, ArrowUpDown, Search, Download, Inbox, Info, ChevronDown } from 'lucide-react';

export const pct = value => `${(value*100).toFixed(1)}%`;
export const num = value => new Intl.NumberFormat('en-IN').format(value);
export const readable = value => value.replaceAll('_',' ');
export const displayItem = item => {
 const [field,...parts]=item.split('=');const value=parts.join('=');
 const name=readable(field).replace(/^./,letter=>letter.toUpperCase());
 return field==='Disease'?readable(value):value?`${name}: ${readable(value)}`:name;
};
export const ruleLabel = rule => `${rule.antecedents.map(displayItem).join(' + ')} → ${rule.consequents.map(displayItem).join(' + ')}`;
export const fmt = value => value == null ? '—' : value.toFixed(3);
export const PALETTE=['#7560d3','#aaa0e7','#67a99a','#b8c9a1','#e1af74','#778da9'];
export function Empty({text='No results match these settings. Try adjusting the filters.',title='No matching patterns'}) {return <div className="empty"><Inbox size={28}/><strong>{title}</strong><p>{text}</p></div>}
export function Panel({title,subtitle,children,action,className=''}) {
 return <section className={`panel ${className}`}><div className="panel-head"><div className="panel-title"><h3>{title}</h3>{subtitle&&<details className="panel-help"><summary aria-label={`About ${title}`}><Info size={15}/></summary><p>{subtitle}</p></details>}</div>{action}</div>{children}</section>;
}
export function Fold({title,children,open=false}) {return <details className="content-fold" open={open||undefined}><summary>{title}<ChevronDown size={16}/></summary><div className="fold-body">{children}</div></details>}
export function ChoiceField({label,value,onChange,options,hint}) {
 return <Field label={label}><select value={value} title={hint} onChange={event=>onChange(event.target.value)}>{options.map(option=>{const [value,text]=Array.isArray(option)?option:[option,option];return <option key={value} value={value}>{text}</option>})}</select></Field>;
}
export function PresetNumberField({label,value,onChange,min=0,max=100000,options=[],hint}) {
 const allowed=options.filter(option=>option>=min&&option<=max);
 if(value!==''&&!allowed.includes(Number(value)))allowed.push(Number(value));
 return <ChoiceField label={label} hint={hint} value={value} onChange={value=>onChange(Number(value))} options={allowed.sort((a,b)=>a-b).map(value=>[value,num(value)])}/>;
}
export function PatternBars({rows,unit='Profiles'}) {
 if(!rows.length)return <Empty/>;
 const maximum=Math.max(...rows.map(row=>row.value),1);
 return <div className="pattern-bars" role="list" aria-label={`Patterns ranked by ${unit.toLowerCase()}`}>{rows.map((row,index)=><div className="pattern-bar-row" role="listitem" key={row.key||index}><div className="pattern-bar-label">{row.rule?<RulePattern rule={row.rule}/>:<span>{row.label}</span>}<strong>{row.formatted||num(row.value)}<small>{unit}</small></strong></div><div className="pattern-bar-track" aria-hidden="true"><span style={{width:`${row.value/maximum*100}%`,background:PALETTE[index%PALETTE.length]}}/></div></div>)}</div>;
}
export function RuleRanking({rules,metric='lift'}) {
 const unit=metric==='lift'?'Lift':'Confidence';
 return <PatternBars unit={unit} rows={rules.map(rule=>({key:ruleLabel(rule),rule,value:metric==='lift'?rule.lift:rule.confidence,formatted:metric==='lift'?`${rule.lift.toFixed(2)}×`:pct(rule.confidence)}))}/>;
}
export function Coverage({count,total}) {
 return <div className="coverage-ring" style={{'--coverage':`${total?count/total*100:0}%`}} role="img" aria-label={`${count} of ${total} disease labels have qualifying rules`}><div><strong>{num(count)}</strong><span>of {num(total)} diseases</span></div></div>;
}
export function Stat({label,value,detail,accent=false}) {return <div className={`stat ${accent?'accent':''}`}><span>{label}</span><strong>{num(value)}</strong><small>{detail}</small></div>}
export function Field({label,children,hint}) {
 const id=useId();
 const controls=React.Children.map(children,child=>React.isValidElement(child)&&['input','select'].includes(child.type)?React.cloneElement(child,{'aria-labelledby':id,'aria-describedby':hint?`${id}-hint`:undefined}):child);
 return <label className="field"><span id={id}>{label}</span>{controls}{hint&&<small id={`${id}-hint`}>{hint}</small>}</label>;
}
export function NumberField({label,value,onChange,min=0,max=1,step=.01,hint}) {return <Field label={label} hint={hint}><input type="number" min={min} max={max} step={step} required value={value} onChange={e=>onChange(e.target.value===''?'':Number(e.target.value))}/></Field>}
export function Bars({data,height=310,xLabel='',vertical=true}) {
 if(!data.length) return <Empty/>;
 return <div style={{height}} className="chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={data} layout={vertical?'vertical':'horizontal'} margin={{left:0,right:24,top:12,bottom:12}}><CartesianGrid strokeDasharray="3 5" horizontal={!vertical} vertical={vertical}/>{vertical?<><XAxis type="number" tick={{fontSize:11}} allowDecimals={false}/><YAxis dataKey="name" type="category" width={150} tick={{fontSize:11}} tickFormatter={v=>v.length>25?v.slice(0,24)+'…':readable(v)}/></>:<><XAxis dataKey="name" tick={{fontSize:11}}/><YAxis tick={{fontSize:11}}/></>}<Tooltip contentStyle={{background:'#fff',color:'#183643',borderRadius:10}} formatter={v=>[v,xLabel||'Records']} labelFormatter={value=>readable(String(value))}/><Bar isAnimationActive={false} dataKey="value" radius={vertical?[0,5,5,0]:[5,5,0,0]} maxBarSize={25}>{data.map((_,i)=><Cell key={i} fill={PALETTE[i%PALETTE.length]}/>)}</Bar></BarChart></ResponsiveContainer></div>
}
export function ScatterPlot({rules,x='support',itemsets=false}) {
 const values=rules.slice(0,1500);
 if(!values.length) return <Empty/>;
 return <div className="scatter-visual"><div className="chart-key"><span>{x==='lift'?'Lift':'Support'} →</span><span>{itemsets?'Items':'Confidence'} ↑</span><span className="bubble-key">Bubble = {itemsets?'profiles':'lift'}</span></div><div className="chart" style={{height:330}}><ResponsiveContainer width="100%" height="100%"><ScatterChart margin={{top:15,right:24,bottom:25,left:5}}><CartesianGrid strokeDasharray="3 5"/><XAxis type="number" dataKey={x} name={readable(x)} tick={{fontSize:11}} label={{value:readable(x),position:'bottom',offset:5}} tickFormatter={x==='support'?pct:undefined}/><YAxis type="number" dataKey={itemsets?'length':'confidence'} name={itemsets?'Length':'Confidence'} domain={itemsets?['auto','auto']:[0,1]} tick={{fontSize:11}} tickFormatter={itemsets?undefined:pct}/><ZAxis type="number" dataKey={itemsets?'item_count':'lift'} range={[30,160]}/><Tooltip content={({active,payload})=>{if(!active||!payload?.length)return null;const r=payload[0].payload;return <div className="plot-tip"><strong>{itemsets?r.itemset.map(displayItem).join(' + '):r.antecedents.map(displayItem).join(' + ')}</strong>{!itemsets&&<p>→ {r.consequents.map(displayItem).join(' + ')}</p>}<p>Support {pct(r.support)} · {r.item_count} records</p>{!itemsets&&<p>Confidence {pct(r.confidence)} · Lift {fmt(r.lift)}</p>}</div>}}/><Scatter isAnimationActive={false} data={values} fill="#8170d9" fillOpacity={.65}/></ScatterChart></ResponsiveContainer></div></div>
}
export function RulePattern({rule}) {return <div className="rule-pattern"><div>{rule.antecedents.map(item=><span className="item" key={item}>{displayItem(item)}</span>)}</div><ArrowRight size={15}/><div>{rule.consequents.map(item=><span className={`item ${item.startsWith('Disease=')?'disease-item':''}`} key={item}>{displayItem(item)}</span>)}</div></div>}
function useTablePages(rows) {
 const [page,setPage]=useState(0),pageSize=10;
 useEffect(()=>setPage(0),[rows]);
 const pages=Math.max(1,Math.ceil(rows.length/pageSize)),current=Math.min(page,pages-1),start=current*pageSize;
 return {rows:rows.slice(start,start+pageSize),current,pages,setPage,label:`${start+1}–${Math.min(start+pageSize,rows.length)} of ${num(rows.length)} selected`};
}
function TablePages({paging}) {
 if(paging.pages<=1)return null;
 return <div className="table-pagination"><span>Page {paging.current+1} of {paging.pages}</span><div><button type="button" className="secondary" aria-label="Previous page" disabled={paging.current===0} onClick={()=>paging.setPage(paging.current-1)}>Previous</button><button type="button" className="secondary" aria-label="Next page" disabled={paging.current===paging.pages-1} onClick={()=>paging.setPage(paging.current+1)}>Next <ArrowRight size={13}/></button></div></div>;
}
export function RuleTable({rules,sort='lift',descending=true,onSort}) {
 const [advanced,setAdvanced]=useState(false),paging=useTablePages(rules);
 if(!rules.length)return <Empty/>;
 return <><div className="table-options"><span>{paging.label}</span><label><input type="checkbox" checked={advanced} onChange={event=>setAdvanced(event.target.checked)}/> Advanced metrics</label></div><div className="table-wrap"><table><thead><tr><th>Association pattern</th>{[['item_count','Count'],['support','Support'],['confidence','Confidence'],['lift','Lift'],['leverage','Leverage'],['conviction','Conviction']].filter(([key])=>advanced||!['leverage','conviction'].includes(key)).map(([key,label])=><th key={key}><button className="sort" onClick={()=>onSort?.(key)} title={`Sort by ${label}`}>{label} {onSort&&<ArrowUpDown size={12}/>} {sort===key?(descending?'↓':'↑'):''}</button></th>)}</tr></thead><tbody>{paging.rows.map(rule=><tr key={JSON.stringify([rule.antecedents,rule.consequents])}><td><RulePattern rule={rule}/></td><td>{rule.item_count}</td><td>{pct(rule.support)}</td><td>{pct(rule.confidence)}</td><td><span className="lift">{rule.lift.toFixed(2)}×</span></td><td hidden={!advanced}>{fmt(rule.leverage)}</td><td hidden={!advanced}>{rule.conviction_infinite?'∞':fmt(rule.conviction)}</td></tr>)}</tbody></table></div><TablePages paging={paging}/></>;
}
export function CombinationTable({rows}) {
 const paging=useTablePages(rows);
 if(!rows.length)return <Empty/>;
 return <><div className="table-options"><span>{paging.label}</span></div><div className="table-wrap"><table><thead><tr><th>Combination</th><th>Items</th><th>Support</th><th>Profiles</th></tr></thead><tbody>{paging.rows.map(row=><tr key={row.itemset.join('|')}><td><div className="items">{row.itemset.map(item=><span className="item" key={item}>{displayItem(item)}</span>)}</div></td><td>{row.length}</td><td>{pct(row.support)}</td><td>{row.item_count}</td></tr>)}</tbody></table></div><TablePages paging={paging}/></>;
}
export function MetricGuide(){return <Fold title="What do support, confidence, and lift mean?"><div className="metric-guide"><div><b>Support</b><p>How often the full pattern appears.</p></div><div><b>Confidence</b><p>Among left-side matches, how often the right side appears.</p></div><div><b>Lift</b><p>How common the outcome is relative to its baseline.</p></div></div></Fold>}
