# Texture reference implementations

Each texture as drawn by the Unslop School course on a 320 by 200 canvas, with `c` the 2d context and `r` a seeded random in [0, 1). Helpers used: `pix(c, fn)` fills every pixel from `fn(x, y) -> [r, g, b]`; `noise(c, amount, r, mono)` adds grain; `g2(x, y, cx, cy, sigma)` is a gaussian blob; `ramp(stops, t)` interpolates a colour ramp; `mix(a, b, t)` lerps two colours.

## Felt texture

Warm, tactile. Games, kids' products, crafts.

```js
(c,r)=>{c.fillStyle="#7B2D3B";c.fillRect(0,0,W,H);for(let i=0;i<9000;i++){const x=r()*W,y=r()*H,a=r()*6.28,l=2+r()*5;c.strokeStyle=r()<.5?"rgba(255,220,220,.10)":"rgba(40,0,10,.18)";c.beginPath();c.moveTo(x,y);c.lineTo(x+Math.cos(a)*l,y+Math.sin(a)*l);c.stroke()}noise(c,22,r)}
```

## Fluted glass

Color seen through ribbed glass. Premium, architectural.

```js
(c,r)=>{pix(c,(x,y)=>{const xs=x+Math.sin((x%16)/16*Math.PI)*10;const v=g2(xs,y,90,80,60)*1.1+g2(xs,y,230,140,70);return ramp([[30,24,60],[240,90,80],[255,200,120]],v)});for(let x=0;x<W;x+=16){const g=c.createLinearGradient(x,0,x+16,0);g.addColorStop(0,"rgba(255,255,255,0)");g.addColorStop(.7,"rgba(255,255,255,.18)");g.addColorStop(1,"rgba(0,0,0,.18)");c.fillStyle=g;c.fillRect(x,0,16,H)}}
```

## Thermal gradients

Heat-camera color. Data, energy, performance.

```js
(c,r)=>pix(c,(x,y)=>ramp([[10,10,60],[90,20,160],[230,40,60],[255,170,30],[255,250,200]],g2(x,y,110,90,55)+g2(x,y,230,130,45)*.8))
```

## Water ripples

Interference rings. Calm, wellness, travel.

```js
(c,r)=>pix(c,(x,y)=>{const a=Math.hypot(x-90,y-80),b=Math.hypot(x-250,y-150);const v=(Math.sin(a*.22)+Math.sin(b*.18))/4+.5;return mix([18,78,96],[150,220,225],v*v)})
```

## Speckled graphite

Dark, mineral, serious. Tools, finance.

```js
(c,r)=>{c.fillStyle="#2A2C31";c.fillRect(0,0,W,H);for(let i=0;i<2600;i++){c.fillStyle=r()<.5?"rgba(255,255,255,"+(.05+r()*.25)+")":"rgba(0,0,0,.35)";const s=r()*1.8+.4;c.fillRect(r()*W,r()*H,s,s)}noise(c,14,r)}
```

## Single-hue landscapes

Layered hills in one color. Outdoor, editorial.

```js
(c,r)=>{c.fillStyle="#E9F0F2";c.fillRect(0,0,W,H);const L=[[200,220,226],[150,185,196],[100,145,162],[58,102,122],[28,62,80]];L.forEach((col,k)=>{c.fillStyle=`rgb(${col})`;c.beginPath();c.moveTo(0,H);const base=70+k*28,ph=r()*6;for(let x=0;x<=W;x+=4)c.lineTo(x,base+Math.sin(x*.02+ph)*14+Math.sin(x*.053+ph*2)*7);c.lineTo(W,H);c.fill()})}
```

## Blueprint grids

Engineering, hardware, developer tools.

```js
(c,r)=>{c.fillStyle="#1C4E8A";c.fillRect(0,0,W,H);for(let x=0;x<=W;x+=10){c.fillStyle=x%50?"rgba(255,255,255,.12)":"rgba(255,255,255,.35)";c.fillRect(x,0,1,H)}for(let y=0;y<=H;y+=10){c.fillStyle=y%50?"rgba(255,255,255,.12)":"rgba(255,255,255,.35)";c.fillRect(0,y,W,1)}c.strokeStyle="rgba(255,255,255,.8)";c.lineWidth=1.2;c.beginPath();c.arc(200,100,40,0,6.28);c.moveTo(150,100);c.lineTo(250,100);c.stroke()}
```

## Halftone

Print and comics. Retro, editorial, zines.

```js
(c,r)=>{c.fillStyle="#F2EEE3";c.fillRect(0,0,W,H);c.fillStyle="#D9472A";for(let y=5;y<H;y+=9)for(let x=5;x<W;x+=9){const v=g2(x,y,190,90,70)+x/W*.25;c.beginPath();c.arc(x+(y/9%2)*4.5,y,Math.min(4.6,v*4.6),0,6.28);c.fill()}}
```

## Grainy gradients

Soft color with film grain. Calmer than a plain gradient.

```js
(c,r)=>{pix(c,(x,y)=>ramp([[255,140,100],[255,200,140],[110,170,160]],x/W*.6+y/H*.4));noise(c,46,r)}
```

## Grass texture

Organic and literal. Sport, garden, outdoors.

```js
(c,r)=>{c.fillStyle="#2E5E22";c.fillRect(0,0,W,H);for(let i=0;i<4500;i++){const x=r()*W,y=r()*(H+20),h=6+r()*14,b=(r()-.5)*6;const g=110+r()*100;c.strokeStyle=`rgba(${g*.45},${g},${g*.3},.8)`;c.lineWidth=1;c.beginPath();c.moveTo(x,y);c.quadraticCurveTo(x+b*.3,y-h*.6,x+b,y-h);c.stroke()}}
```

## Dithered images

Two-tone pixel shading. Use with an intent, not as decoration.

```js
(c,r)=>{const B=[0,8,2,10,12,4,14,6,3,11,1,9,15,7,13,5];pix(c,(x,y)=>{const dx=x-160,dy=y-100,d=Math.hypot(dx,dy)/80;let v=d<1?(.25+.75*Math.max(0,(-dx-dy*.8+60)/170))*1:.12+y/H*.15;return v>(B[(y%4)*4+x%4]+.5)/16?[236,230,214]:[24,26,48]})}
```

## Paper texture

Publishing, stationery, anything about writing.

```js
(c,r)=>{c.fillStyle="#EFE8D9";c.fillRect(0,0,W,H);for(let i=0;i<500;i++){c.strokeStyle="rgba(120,100,70,.08)";c.beginPath();const x=r()*W,y=r()*H;c.moveTo(x,y);c.lineTo(x+(r()-.5)*30,y+(r()-.5)*6);c.stroke()}noise(c,16,r)}
```

## Contour lines

Topographic maps. Outdoors, data, geography.

```js
(c,r)=>pix(c,(x,y)=>{const f=g2(x,y,100,90,60)*1.2+g2(x,y,240,120,50)+g2(x,y,200,30,40)*.6;const k=(f*12)%1;return k<.09?[220,120,60]:[247,241,230]})
```

## Cloud sky

Airy and optimistic. Travel, weather, consumer.

```js
(c,r)=>{const g=c.createLinearGradient(0,0,0,H);g.addColorStop(0,"#5C9BDB");g.addColorStop(1,"#BFDDF5");c.fillStyle=g;c.fillRect(0,0,W,H);for(let i=0;i<70;i++){const x=r()*W,y=40+r()*120,s=14+r()*30;const rg=c.createRadialGradient(x,y,0,x,y,s);rg.addColorStop(0,"rgba(255,255,255,.5)");rg.addColorStop(1,"rgba(255,255,255,0)");c.fillStyle=rg;c.fillRect(x-s,y-s,s*2,s*2)}}
```

## Pixel mosaics

Chunky color blocks. Games, playful brands.

```js
(c,r)=>{const P=["#264653","#2A9D8F","#E9C46A","#F4A261","#E76F51"];for(let y=0;y<H;y+=16)for(let x=0;x<W;x+=16){const v=(g2(x,y,120,100,80)+x/W*.4+r()*.25);c.fillStyle=P[Math.min(4,Math.floor(v*3.2))];c.fillRect(x,y,16,16)}}
```

## Lens distortion

A grid bending as if behind glass. Optics, cameras, AR.

```js
(c,r)=>pix(c,(x,y)=>{const nx=(x-160)/160,ny=(y-100)/160,rr=nx*nx+ny*ny,k=1+.9*rr;const u=nx*k*160+160,v=ny*k*160+100;const on=Math.abs((u%20+20)%20-10)>9||Math.abs((v%20+20)%20-10)>9;return on?[245,245,250]:mix([20,22,40],[60,40,120],rr)})
```

## Stippled gradients

Dots that thin out. Hand-made, scientific illustration.

```js
(c,r)=>{c.fillStyle="#F3EFE6";c.fillRect(0,0,W,H);c.fillStyle="#1F2A44";for(let i=0;i<14000;i++){const x=r()*W,y=r()*H;if(r()<Math.pow(1-x/W,1.6)*.9)c.fillRect(x,y,1.3,1.3)}}
```

## Square-dot grids

A quiet technical ground. Dashboards, docs.

```js
(c,r)=>{c.fillStyle="#F5F6F8";c.fillRect(0,0,W,H);for(let y=6;y<H;y+=12)for(let x=6;x<W;x+=12){c.fillStyle=`rgba(40,50,80,${.15+g2(x,y,160,100,90)*.6})`;c.fillRect(x,y,3,3)}}
```

## Blurred photos

A photo turned into soft color fields. Keeps mood, drops detail.

```js
(c,r)=>{c.fillStyle="#3B2E2A";c.fillRect(0,0,W,H);[[60,60,110,"230,150,90"],[230,70,100,"120,150,190"],[170,170,120,"60,90,70"],[300,170,90,"240,210,170"]].forEach(b=>{const g=c.createRadialGradient(b[0],b[1],0,b[0],b[1],b[2]);g.addColorStop(0,`rgba(${b[3]},.95)`);g.addColorStop(1,`rgba(${b[3]},0)`);c.fillStyle=g;c.fillRect(0,0,W,H)})}
```

## Iridescent shapes

Oil-slick color on a single form. Beauty, fashion.

```js
(c,r)=>pix(c,(x,y)=>{const d=Math.hypot(x-160,(y-100)*1.3);if(d>78)return[242,240,245];const t=(Math.atan2(y-100,x-160)/6.28+d/60)%1;const h=t*6.28;return[200+50*Math.sin(h),200+50*Math.sin(h+2.1),210+45*Math.sin(h+4.2)]})
```

## Impressionist paintings

Visible brushwork. Culture, food, hospitality.

```js
(c,r)=>{c.fillStyle="#8DB7D6";c.fillRect(0,0,W,H);for(let i=0;i<3200;i++){const x=r()*W,y=r()*H;let col=y<110?[120+r()*60,170+r()*50,215+r()*30]:[60+r()*60,120+r()*60,60+r()*40];if(g2(x,y,240,50,26)>.4)col=[255,200+r()*40,90+r()*60];c.strokeStyle=`rgba(${col.map(Math.round)},.75)`;c.lineWidth=2.5+r()*2;c.lineCap="round";c.beginPath();const a=y<110?-.2:.4;c.moveTo(x,y);c.lineTo(x+Math.cos(a+r()*.5)*8,y+Math.sin(a+r()*.5)*8);c.stroke()}}
```

## ASCII and pixels

Characters as pixels. Developer brands, when it means something.

```js
(c,r)=>{c.fillStyle="#0E1220";c.fillRect(0,0,W,H);c.font="8px monospace";c.textBaseline="top";const ch=" .:-=+*#%@";for(let y=0;y<H;y+=9)for(let x=0;x<W;x+=6){const v=g2(x,y,160,100,55)+g2(x,y,60,40,25)*.6;const i=Math.min(9,Math.floor(v*9));c.fillStyle=`rgba(120,230,170,${.35+v*.65})`;c.fillText(ch[i],x,y)}}
```
