const DAN=process.env.DAN;const fs=require('fs');const h=fs.readFileSync('index32.html','utf8');const src=h.split('<script>')[1].split('</script>')[0];
const C={};global.window={};global.Option=function(t,v){this.text=t;this.value=v};
const L=f=>JSON.parse(fs.readFileSync(f));
const ig=L('igraci2.json'); const ex=new Set(ig.filter(r=>r.iskljuci).map(r=>r.igrac));
const kv=L('kvote.json').filter(k=>!ex.has(k.igrac));
const dash={calc:(id,d)=>{C[id]=d},draw:()=>{},onData:()=>{},data:()=>({status:'loading',data:[]})};
const mk=()=>({children:[],replaceChildren(){},appendChild(){},append(){},dataset:{},style:{}});
new Function('dash','d3','document',src)(dash,{format:()=>x=>x,max:()=>1},{createElement:mk,querySelectorAll:()=>[],getElementById:()=>null,createTextNode:t=>t});
// Od 6.11.2026. jedna lista: preporuke, dopunjene opkladama sa glavnih linija kojih nema (drugi igrač), najviše 3 po utakmici, po vrednosti
const fri=C.preporuke.fn(ig,kv).filter(x=>x.termin.startsWith(DAN));
const imaju=new Set(fri.map(x=>x.igrac)), poUt=new Map(); for(const x of fri) poUt.set(x.utakmica,(poUt.get(x.utakmica)||0)+1);
for(const x of C.glavne.fn(ig,kv).filter(x=>x.termin.startsWith(DAN))){
  if(imaju.has(x.igrac)||(poUt.get(x.utakmica)||0)>=3)continue;
  fri.push({...x,kljuc:'K'+x.kolo+' '+x.igrac+' '+x.kategorija,grupa:'Takođe verujem',rang:fri.length+1}); imaju.add(x.igrac); poUt.set(x.utakmica,(poUt.get(x.utakmica)||0)+1);
}
fri.sort((a,b)=>(a.grupa==='Najsigurnije'?0:1)-(b.grupa==='Najsigurnije'?0:1)||b.vrednost-a.vrednost); fri.forEach((x,i)=>x.rang=i+1);
fs.writeFileSync('picks_pet3.json',JSON.stringify(fri));
fs.writeFileSync('glavne_pet.json','[]');   // posebna lista glavnih linija više ne postoji
for(const x of fri) console.log(x.grupa,'|',x.igrac,'|',x.utakmica,'|',x.opklada,x.kvota,x.sansa,x.istorija,'ev',x.vrednost,'z',x.razmak,'min',x.minuti);
