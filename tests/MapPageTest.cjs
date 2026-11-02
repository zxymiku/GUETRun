// Uses a local AMap stub: checks editor interactions, not the live map service.
const fs=require('fs'),path=require('path'),os=require('os'),assert=require('assert');
const { chromium }=require('playwright');
const html=fs.readFileSync(path.join(__dirname,'../app/src/main/assets/route-map.html'),'utf8');
const stub=`(function(){
class LngLat {constructor(lng,lat){this.lng=lng;this.lat=lat}getLat(){return this.lat}getLng(){return this.lng}}
class Map {constructor(id,options){this.element=document.getElementById(id);this.center=new LngLat(...options.center);this.events={};this.status={};window.testMap=this;this.element.style.background='#e8eee8';}
 on(n,f){this.events[n]=f;if(n==='complete')setTimeout(f,1)}addControl(){}setStatus(s){Object.assign(this.status,s)}
 setFitView(){}getCenter(){return this.center}setCenter(p){this.center=p instanceof LngLat?p:new LngLat(...p);this.events.mapmove?.()}
 setLayers(){}setZoomAndCenter(z,p){this.setCenter(p)}
 containerToLngLat(p){const b=this.element.getBoundingClientRect();return new LngLat(this.center.lng+(p.x-b.width/2)/100000,this.center.lat-(p.y-b.height/2)/100000)}
 lngLatToContainer(p){const b=this.element.getBoundingClientRect();return {x:(p[0]-this.center.lng)*100000+b.width/2,y:(this.center.lat-p[1])*100000+b.height/2}}
}
class Marker {setMap(){}hide(){}show(){}setPosition(){}}
class Polyline {constructor(){window.testLine=this;}setMap(m){this.map=m;this.svg=document.createElementNS('http://www.w3.org/2000/svg','svg');this.svg.style='width:100%;height:100%;position:absolute;pointer-events:none';this.map.element.append(this.svg)}
 setPath(p){this.path=p;this.svg.innerHTML='<polyline points="'+p.map(q=>{const a=this.map.lngLatToContainer(q);return a.x+','+a.y}).join(' ')+'" fill="none" stroke="#007765" stroke-width="4"/>'}}
class PlaceSearch {search(q,callback){callback('complete',{poiList:{pois:[{name:'测试地点',cityname:'北京',adname:'东城',location:new LngLat(116.4,39.9)}]}})}}
class TileLayer{};TileLayer.Satellite=class{};TileLayer.RoadNet=class{};
window.AMap={Map,Marker,Polyline,PlaceSearch,LngLat,TileLayer,Scale:class{},ToolBar:class{},Pixel:class{constructor(x,y){this.x=x;this.y=y}}};})();`;
const near=(a,b,tol,label)=>assert(Math.abs(a-b)<=tol,`${label}: ${a} vs ${b}`);
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.MAP_TEST_BROWSER||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:393,height:852},isMobile:true,hasTouch:true});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('dialog',()=>assert.fail('Editing should not depend on native confirm dialogs'));
  await page.route('https://webapi.amap.com/**',r=>r.fulfill({contentType:'application/javascript',body:stub}));
  const load=async state=>{await page.goto('about:blank');await page.setContent(html);await page.evaluate(s=>{window.RouteApp={save:v=>window.savedRoute=JSON.parse(v)};window.boot(s)},state)};
  const ready=()=>page.waitForFunction(()=>window.testMap&&window.testLine&&testMap.events.click);
  const initial={key:'test-key',security:'test-security',center:[39.9,116.4]};
  await load({...initial,key:'',security:''});assert(await page.locator('#save').isDisabled());assert((await page.locator('#message').innerText()).includes('尚未配置'));
  await load(initial);await ready();
  const settle=()=>page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
  const clickMap=async(lat,lon)=>{await page.evaluate(([a,b])=>testMap.events.click({lnglat:new AMap.LngLat(b,a)}),[lat,lon]);await settle()};
  const save=async()=>{await settle();await page.locator('#save').click();return page.evaluate(()=>savedRoute)};
  const routeLength=route=>page.evaluate(r=>RouteGeometry.pathLength(r.points.map(RouteGeometry.wgs),r.closed),route);
  const drag=async(selector,dx,dy)=>{const b=await page.locator(selector).boundingBox();assert(b,selector);await page.mouse.move(b.x+b.width/2,b.y+b.height/2);await page.mouse.down();await page.mouse.move(b.x+b.width/2+dx,b.y+b.height/2+dy,{steps:8});await page.mouse.up();await settle()};
  // Geometry is evaluated independently of the screen projection.
  const shape=await page.evaluate(()=>{const g=RouteGeometry,t=g.stadium([39.9,116.4],400,.42195,90);return {length:g.pathLength(t.wgs,true),edges:t.wgs.map((p,i)=>g.distance(p,t.wgs[(i+1)%t.wgs.length]))}});
  near(shape.length,400,.002,'400m measured perimeter');assert(shape.edges.filter(e=>e>80).length===2,'Stadium must contain two long straight sections');
  await clickMap(39.9,116.4);let saved=await save();assert.equal(saved.mode,'track');assert.equal(saved.closed,true);assert.equal(saved.laps,1);near(await routeLength(saved),400,.01,'Track saved length');
  await page.locator('#laps').fill('5');saved=await save();assert.equal(saved.laps,5);assert((await page.locator('#stats').innerText()).includes('2.000 km'));
  await page.locator('#preset800').click();near(await routeLength(await save()),800,.01,'800m preset');
  await page.locator('#perimeter').fill('600');await page.locator('#perimeter').press('Tab');near(await routeLength(await save()),600,.01,'Numeric perimeter');
  await page.locator('#undo').click();near(await routeLength(await save()),800,.01,'Undo perimeter');
  await page.locator('#redo').click();near(await routeLength(await save()),600,.01,'Redo perimeter');
  await page.locator('#preset400').click();
  await page.locator('#scale').evaluate(e=>{e.dispatchEvent(new PointerEvent('pointerdown'));e.value=150;e.dispatchEvent(new Event('input'))});
  near(await routeLength(await save()),600,.01,'Scale slider');
  await page.locator('#ratio').evaluate(e=>{e.dispatchEvent(new PointerEvent('pointerdown'));e.value=65;e.dispatchEvent(new Event('input'))});
  saved=await save();near(saved.editor.ratio,.65,.0001,'Shape ratio');near(await routeLength(saved),600,.01,'Ratio preserves perimeter');
  await page.locator('#rotate90').click();saved=await save();near(saved.editor.bearing,180,.001,'Rotation');
  await page.locator('#preset400').click();await page.locator('#angle').evaluate(e=>{e.value=90;e.dispatchEvent(new Event('input'))});await settle();
  const before=await save();await drag('.handle.scale',30,20);saved=await save();assert(Math.abs(saved.editor.perimeter-before.editor.perimeter)>10,'Handle must resize the track');near(await routeLength(saved),saved.editor.perimeter,.01,'Dragged perimeter');
  await drag('.handle.center',8,10);saved=await save();assert.notDeepEqual(saved.center,before.center,'Center handle must move course');
  await drag('.handle.rotate',-15,35);saved=await save();assert(Math.abs(saved.editor.bearing-before.editor.bearing)>5,'Handle must rotate course');
  await page.locator('#laps').fill('1001');await settle();assert(await page.locator('#save').isDisabled());await page.locator('#laps').fill('5');
  // Opening a saved course must preserve editable track parameters and lap count.
  const stored=await save();const centerWgs=await page.evaluate(c=>RouteGeometry.wgs(c),stored.center);
  await load({...initial,...stored,editor:{...stored.editor,center:centerWgs}});await ready();saved=await save();near(saved.editor.perimeter,stored.editor.perimeter,.0001,'Restored perimeter');assert.equal(saved.laps,5);assert.equal(await page.locator('.handle').count(),3);
  // Repeated point selection and mode changes must work after a route exists.
  await page.locator('[data-mode=point]').click();await clickMap(39.9001,116.4001);await clickMap(39.9002,116.4002);saved=await save();assert.equal(saved.mode,'point');assert.deepEqual(saved.center,[39.9002,116.4002]);
  await page.locator('[data-mode=line]').click();await clickMap(39.9,116.4);await clickMap(39.9005,116.4);await clickMap(39.9005,116.4008);saved=await save();assert.equal(saved.points.length,3);
  await drag('.vertex[data-index="1"]',20,10);saved=await save();assert.notDeepEqual(saved.points[1],[39.9005,116.4],'Vertex drag');
  await page.locator('#undo').click();saved=await save();assert.deepEqual(saved.points[1],[39.9005,116.4]);await page.locator('#redo').click();const edited=await save();
  await page.locator('[data-mode=point]').click();assert.deepEqual((await save()).center,[39.9002,116.4002],'Point draft retained');
  await page.locator('[data-mode=line]').click();assert.deepEqual((await save()).points,edited.points,'Line draft retained');
  await page.locator('#closed').uncheck();saved=await save();assert.equal(saved.closed,false);assert.equal(saved.laps,0);assert(await page.locator('#use-laps').isDisabled());
  await page.locator('#closed').check();await page.locator('#use-laps').check();await page.locator('#laps').fill('3');assert.equal((await save()).laps,3);
  await page.locator('#clear').click();assert(await page.locator('#save').isDisabled());await page.locator('#undo').click();assert.deepEqual((await save()).points,edited.points);
  await page.locator('#search').fill('北京 公园');await page.locator('#search-form button').first().click();await page.locator('#search-results button').click();assert.equal(await page.locator('#search-results').isVisible(),false);
  // A second stroke appends to the first; canceled input restores the previous path.
  await page.locator('[data-mode=draw]').click();let box=await page.locator('#draw-layer').boundingBox();
  const stroke=async coords=>{await page.mouse.move(box.x+coords[0][0],box.y+coords[0][1]);await page.mouse.down();for(const [x,y] of coords.slice(1))await page.mouse.move(box.x+x,box.y+y,{steps:6});await page.mouse.up();await settle()};
  await stroke([[35,35],[70,45],[100,90],[145,60]]);const first=await save();assert(first.points.length>=4,'Curved finger stroke must retain its turns');
  await stroke([[145,60],[190,110],[225,80],[250,130]]);const second=await save();assert(second.points.length>first.points.length,'Second stroke must append');assert.deepEqual(second.points.slice(0,first.points.length),first.points,'Earlier stroke must be retained');
  await page.locator('#undo').click();assert.deepEqual((await save()).points,first.points);await page.locator('#redo').click();assert.deepEqual((await save()).points,second.points);
  await page.mouse.move(box.x+250,box.y+130);await page.mouse.down();await page.mouse.move(box.x+280,box.y+150);await page.locator('#draw-layer').evaluate(e=>e.dispatchEvent(new PointerEvent('pointercancel',{pointerId:1,bubbles:true})));await page.mouse.up();assert.deepEqual((await save()).points,second.points,'Canceled stroke');
  await page.locator('#gesture').click();assert.equal(await page.locator('#draw-layer').isVisible(),false);await clickMap(39.899,116.399);await page.locator('#gesture').click();assert.deepEqual((await save()).points,second.points,'Panning retains drawing');
  await page.locator('[data-mode=track]').click();
  for(const viewport of [{width:393,height:852},{width:360,height:640}]){await page.setViewportSize(viewport);await settle();assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),JSON.stringify(await page.evaluate(()=>[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>({tag:e.tagName,id:e.id,cls:e.className,right:e.getBoundingClientRect().right,text:e.textContent.slice(0,30)})))));const b=await page.locator('#map-wrap').boundingBox();assert(b.height>=150,'Map usable height');const saveBox=await page.locator('#save').boundingBox();assert(saveBox.y+saveBox.height<=viewport.height+1,'Save button must remain reachable');}
  await page.setViewportSize({width:393,height:752});await page.locator('#preset400').click();await page.locator('#place-track').click();await settle();await page.screenshot({path:path.join(os.tmpdir(),'map-editor-v2-test.png')});
  assert.equal(errors.length,0,errors.join('\n'));console.log('Map editor passed: mobile layout, repeated points, stadium shape, scale/rotate/move, laps, restore, drafts, line edits, multi-stroke drawing, undo/redo and cancel (stub API).');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
