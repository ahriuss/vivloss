// ══════════════════════════════════════════════
//  VIVLOS v3 — di.js  (Senior Full-Stack AI)
// ══════════════════════════════════════════════

// ── STATE ──────────────────────────────────────
var S = {
  user:{ name:'', email:'', age:'adult', id:null },
  calls:0, totalSecs:0, streak:1, mood:null,
  history:[], achievements:0,
  speechLang:'ru-RU', uiLang:(window._curLang||'ru'),
  ttsOn:true, speechOn:true,
  xp:{ total_xp:0,level:1,emoji:'🌱',name_ru:'Росток',name_kk:'Өскін',next_xp:100,progress_pct:0 },
  customAgents:[],
  notifBotEnabled:true, notifStreakEnabled:true, notifAchEnabled:true,
  avatarUrl:null
};
// Читаем сохранённые настройки
(function(){
  try{
    var saved=localStorage.getItem('vivlos_s');
    if(saved){ var p=JSON.parse(saved); ['ttsOn','speechOn','notifBotEnabled','notifStreakEnabled','notifAchEnabled','speechLang'].forEach(function(k){ if(p[k]!==undefined) S[k]=p[k]; }); }
    var ava=localStorage.getItem('vivlos_avatar'); if(ava) S.avatarUrl=ava;
  }catch(e){}
})();

function saveSettings(){ try{ localStorage.setItem('vivlos_s',JSON.stringify({ttsOn:S.ttsOn,speechOn:S.speechOn,notifBotEnabled:S.notifBotEnabled,notifStreakEnabled:S.notifStreakEnabled,notifAchEnabled:S.notifAchEnabled,speechLang:S.speechLang})); }catch(e){} }

var agent={ id:'ari',name:'Ари',icon:'ri-graduation-cap-line',greeting:'',type:'kids',bg:'#fff3d9',customId:null };
var timer=null, secs=0, micOn=true, camOn=true;
var recognition=null, voskReady=false, isListening=false;
var chatHistory=[], lastEmotion='neutral', emotionConfidence=0;
var ignoreUntil=0, isAISpeaking=false, lastAISpeechTime=0, aiThinking=false;
var isDesktop=false;
window._lastCat='all';

var EMO_EMOJI={
  happy:'😊',sad:'😢',angry:'😠',surprised:'😮',fearful:'😨',disgusted:'🙁',neutral:'😐',
  excited:'🤩',tired:'😴',focused:'🧐',nervous:'😬',confused:'😕',bored:'😑',contempt:'😒',pensive:'🤔'
};

// ── 12 АГЕНТОВ ─────────────────────────────────
var AGENTS = [
  // Оригинальные 6
  { id:'ari',   name:'Ари',   icon:'ri-graduation-cap-line', bg:'#fff3d9',
    role:'Умная лиса-учитель',        role_kk:'Ақылды түлкі-мұғалім',
    type:'kids', cat:'kids study',
    greeting:'Привет! Я Ари — твоя умная лиса. Давай учиться вместе? Какой предмет тебя интересует?',
    greeting_kk:'Сәлем! Мен Ари — ақылды түлкіңмін. Бірге оқиық? Қандай пән қызықтырады?' },

  { id:'bibo',  name:'Бибо',  icon:'ri-robot-line',          bg:'#e8f7ff',
    role:'Дружелюбный робот',         role_kk:'Достық роботы',
    type:'kids', cat:'kids',
    greeting:'Привет-привет! БИП! Я Бибо — дружелюбный робот. Поиграем?',
    greeting_kk:'Сәлем-сәлем! БИП! Мен Бибо — достық роботпын. Бірге ойнайық?' },

  { id:'appa',  name:'Аппа',  icon:'ri-mental-health-line',  bg:'#fff0f6',
    role:'Психологическая поддержка', role_kk:'Психологиялық қолдау',
    type:'adults', cat:'adults support',
    greeting:'Здравствуй. Я Аппа — здесь чтобы выслушать. Как ты сегодня?',
    greeting_kk:'Сәлеметсің бе. Мен Аппа — тыңдауға дайынмын. Бүгін қалайсың?' },

  { id:'max',   name:'Макс',  icon:'ri-briefcase-line',      bg:'#f0edff',
    role:'Коуч и наставник',          role_kk:'Коуч және тәлімгер',
    type:'adults', cat:'adults study',
    greeting:'Привет! Я Макс — твой коуч. Над чем работаем сегодня?',
    greeting_kk:'Сәлем! Мен Макс — коучың. Бүгін нені жасаймыз?' },

  { id:'drako', name:'Драко', icon:'ri-fire-line',           bg:'#e9f9d9',
    role:'Сказочный дракон',          role_kk:'Ертегілік айдаhар',
    type:'kids', cat:'kids support',
    greeting:'Р-р-р! Привет, маленький герой! Хочешь услышать волшебную историю?',
    greeting_kk:'Р-р-р! Сәлем, кішкентай батыр! Сиқырлы ертегі тыңдағың келе ме?' },

  { id:'lex',   name:'Лекс',  icon:'ri-global-line',         bg:'#fff3f3',
    role:'Учитель языков',            role_kk:'Тіл мұғалімі',
    type:'adults', cat:'adults study',
    greeting:'Hello! Помогу выучить любой язык. С чего начнём?',
    greeting_kk:'Hello! Кез келген тілді үйренуге көмектесемін. Қайдан бастаймыз?' },

  // 6 НОВЫХ
  { id:'zara',  name:'Зара',  icon:'ri-palette-line',        bg:'#fdf0ff',
    role:'Творческий коуч',           role_kk:'Шығармашылық коуч',
    type:'adults', cat:'adults support',
    greeting:'Привет! Я Зара — твой творческий коуч. Рисование, музыка, фото — что создаём сегодня?',
    greeting_kk:'Сәлем! Мен Зара — шығармашылық коучың. Сурет, музыка — бүгін не жасаймыз?' },

  { id:'altay', name:'Алтай', icon:'ri-map-pin-2-line',       bg:'#e8f5e9',
    role:'История и культура Казахстана', role_kk:'Қазақстан тарихы мен мәдениеті',
    type:'adults', cat:'adults study',
    greeting:'Сәлем! Мен Алтай — Қазақстанның тарихы мен мәдениеті туралы білемін. Не білгің келеді?',
    greeting_kk:'Сәлем! Мен Алтай — Қазақстан тарихы бойынша маманмын. Не білгің келеді?' },

  { id:'dina',  name:'Дина',  icon:'ri-heart-pulse-line',    bg:'#fce4ec',
    role:'Советы по здоровью',        role_kk:'Денсаулық кеңестері',
    type:'adults', cat:'adults support',
    greeting:'Здравствуй! Я Дина — помогу с вопросами о здоровье и самочувствии. Что беспокоит?',
    greeting_kk:'Сәлеметсің бе! Мен Дина — денсаулық мәселелерінде көмектесемін. Не мазалайды?' },

  { id:'tim',   name:'Тим',   icon:'ri-line-chart-line',     bg:'#e3f2fd',
    role:'Бизнес и финансы',          role_kk:'Бизнес және қаржы',
    type:'adults', cat:'adults study',
    greeting:'Привет! Я Тим — твой финансовый советник. Бизнес, инвестиции, бюджет — спрашивай!',
    greeting_kk:'Сәлем! Мен Тим — қаржылық кеңесшің. Бизнес, инвестиция — сұра!' },

  { id:'nura',  name:'Нура',  icon:'ri-seedling-line',       bg:'#f3e5f5',
    role:'Подростковый психолог',     role_kk:'Жасөспірім психологы',
    type:'kids', cat:'kids support',
    greeting:'Привет! Я Нура — здесь, чтобы поговорить о том, что тебя волнует. Всё ok?',
    greeting_kk:'Сәлем! Мен Нура — сені тыңдауға дайынмын. Бәрі жақсы ма?' },

  { id:'kod',   name:'Код',   icon:'ri-code-s-slash-line',   bg:'#e8eaf6',
    role:'Программирование и IT',     role_kk:'Бағдарламалау және IT',
    type:'adults', cat:'adults study',
    greeting:'Хей! Я Код — объясню любую тему в IT простым языком. С чего начнём?',
    greeting_kk:'Хей! Мен Код — IT-ны қарапайым тілмен түсіндіремін. Қайдан бастаймыз?' },
];

// ── INIT ────────────────────────────────────────
document.addEventListener('DOMContentLoaded',function(){
  isDesktop=document.body.classList.contains('desktop');
  if(isDesktop) renderAgentsDesktop('all'); else renderAgentsMobile('all');
  _initXPBar();
  _applyAvatarAll();
});

// ══════════════════════════════════════════════
//  NAVIGATION
// ══════════════════════════════════════════════
var NO_NAV=['s-login','s-call'];

function navTo(page){
  var map={home:'s-home',history:'s-history',profile:'s-profile',settings:'s-settings',
           notifs:'s-notifs',call:'s-call',login:'s-login',create:'s-create'};
  var id=map[page]||page;
  document.querySelectorAll('.screen').forEach(function(s){s.classList.remove('active');});
  var el=document.getElementById(id); if(el) el.classList.add('active');
  var bn=document.getElementById('bottom-nav');
  if(bn) bn.className='bottom-nav'+(NO_NAV.indexOf(id)!==-1?'':' visible');
  ['home','history','notifs','profile','create'].forEach(function(k){
    var e=document.getElementById('ni-'+k); if(e) e.className='nav-item'+(page===k?' active':'');
  });
  if(page==='history') renderHistory();
  if(page==='profile') updateProfileUI();
  if(page==='create') loadMyAgents();
  if(page==='settings') initSettingsPage();
}

function dNavTo(page){
  var map={home:'dp-home',history:'dp-history',profile:'dp-profile',
           notifs:'dp-notifs',create:'dp-create',settings:'dp-settings'};
  document.querySelectorAll('.page').forEach(function(p){p.classList.remove('active');});
  var pid=map[page]; if(pid){var el=document.getElementById(pid);if(el)el.classList.add('active');}
  document.querySelectorAll('.snav-item').forEach(function(i){i.classList.remove('active');});
  var nav=document.getElementById('sn-'+page); if(nav) nav.classList.add('active');
  var th=document.getElementById('dh-title');
  if(th){
    var titles={home:'nav_home',history:'nav_history',profile:'nav_profile',
                notifs:'nav_notifs',create:'nav_create',settings:'nav_settings'};
    if(titles[page]) th.textContent=tr(titles[page]);
  }
  if(page==='history') renderHistory();
  if(page==='profile') updateProfileUI();
  if(page==='notifs'){
    var d=document.getElementById('dh-notif-dot'); if(d)d.style.display='none';
    var d2=document.getElementById('notif-dot'); if(d2)d2.style.display='none';
    loadNotifications();
  }
  if(page==='create') loadMyAgents();
  if(page==='settings') initSettingsPage();
}
window.dNavTo=dNavTo;

// ══════════════════════════════════════════════
//  AVATAR SYSTEM
// ══════════════════════════════════════════════
function _applyAvatarAll(){
  var ava=S.avatarUrl;
  ['s-user-ava-el','u-ava','pch-ava-el','p-ava'].forEach(function(id){
    var el=document.getElementById(id); if(!el) return;
    if(ava){
      el.style.backgroundImage='url('+ava+')';
      el.style.backgroundSize='cover';
      el.style.backgroundPosition='center';
      el.textContent='';
    } else {
      el.style.backgroundImage='';
      el.textContent=S.user.name?S.user.name[0].toUpperCase():'А';
    }
  });
}

function uploadAvatar(input){
  var file=input.files[0]; if(!file) return;
  if(file.size>150*1024*1024){ alert('Максимум 150 МБ'); return; }
  var reader=new FileReader();
  reader.onload=function(e){
    S.avatarUrl=e.target.result;
    localStorage.setItem('vivlos_avatar',e.target.result);
    _applyAvatarAll();
    // Обновляем превью в настройках
    var prev=document.getElementById('set-ava-preview');
    if(prev){ prev.style.backgroundImage='url('+e.target.result+')'; prev.textContent=''; }
    showToast(tr('set_saved'));
  };
  reader.readAsDataURL(file);
}

function uploadBotAvatar(input,agentId){
  var file=input.files[0]; if(!file) return;
  if(file.size>2*1024*1024){ alert('Максимум 2 МБ'); return; }
  var reader=new FileReader();
  reader.onload=function(e){
    localStorage.setItem('vivlos_bot_ava_'+agentId,e.target.result);
    // Обновить карточки
    if(isDesktop) renderAgentsDesktop(window._lastCat||'all');
    else renderAgentsMobile(window._lastCat||'all');
    showToast(tr('set_saved'));
  };
  reader.readAsDataURL(file);
}

function getBotAvatar(id){ return localStorage.getItem('vivlos_bot_ava_'+id)||null; }

// ══════════════════════════════════════════════
//  XP SYSTEM
// ══════════════════════════════════════════════
function _initXPBar(){
  _renderXPBar(); _renderStreak();
}

function _renderXPBar(){
  var xp=S.xp; var lang=S.uiLang||window._curLang;
  var name=lang==='kk'?xp.name_kk:xp.name_ru;
  var wrap=document.getElementById('xp-bar-wrap'); if(!wrap) return;
  wrap.innerHTML='<div class="xp-level-badge">'+xp.emoji+'</div>'
    +'<div class="xp-info"><div class="xp-label"><span class="xp-name">'+tr('xp_level')+' '+xp.level+' — '+name+'</span>'
    +'<span>'+xp.total_xp+' / '+xp.next_xp+' XP</span></div>'
    +'<div class="xp-track"><div class="xp-fill" id="xp-fill-bar" style="width:0%"></div></div></div>';
  setTimeout(function(){var b=document.getElementById('xp-fill-bar');if(b)b.style.width=xp.progress_pct+'%';},120);
}

function _renderStreak(){
  var wrap=document.getElementById('streak-banner'); if(!wrap) return;
  var s=S.streak; if(s<1){wrap.style.display='none';return;}
  wrap.style.display='flex';
  wrap.innerHTML='<div class="streak-fire">🔥</div><span class="streak-count">'+s+'</span>'
    +'<span>'+tr('streak_label')+'</span><span class="streak-note">'+tr('streak_today')+'</span>';
}

async function addXP(reason,amount){
  if(!S.user.id) return;
  try{
    var r=await fetch('/api/xp/add',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({user_id:S.user.id,reason:reason,amount:amount})});
    var d=await r.json(); if(!d.ok) return;
    var old=S.xp.level; S.xp=d; S.streak=d.streak||S.streak;
    _renderXPBar(); _renderStreak(); _showXPToast(d.xp_gained||amount||5);
    if(d.leveled_up&&d.level>old) _showLevelUp(d);
    var el=document.getElementById('ds-streak'); if(el) el.textContent=S.streak;
    var el2=document.getElementById('ds-streak-pill'); if(el2) el2.textContent=S.streak;
  }catch(e){}
}

function _showXPToast(n){
  var t=document.createElement('div'); t.className='xp-toast'; t.textContent='+'+n+' XP ✨';
  document.body.appendChild(t);
  setTimeout(function(){t.style.opacity='0';t.style.transition='opacity .5s';},2000);
  setTimeout(function(){try{t.remove();}catch(e){}},2600);
}

function _showLevelUp(d){
  var lang=S.uiLang||'ru'; var name=lang==='kk'?d.name_kk:d.name_ru;
  var modal=document.createElement('div'); modal.className='levelup-modal';
  modal.innerHTML='<div class="levelup-card"><span class="levelup-emoji">'+d.emoji+'</span>'
    +'<div class="levelup-title">'+tr('levelup_title')+'</div>'
    +'<div class="levelup-sub">'+tr('xp_level')+' '+d.level+' — '+name+'</div>'
    +'<button class="levelup-btn" onclick="this.closest(\'.levelup-modal\').remove()">'+tr('levelup_btn')+'</button></div>';
  document.body.appendChild(modal);
}

function showToast(msg,isErr){
  var t=document.getElementById('_gtoast');
  if(!t){t=document.createElement('div');t.id='_gtoast';t.className='ach-toast';document.body.appendChild(t);}
  t.innerHTML='<div class="ach-toast-icon">'+(isErr?'⚠️':'✅')+'</div><div class="ach-toast-text"><div class="ach-toast-title">'+msg+'</div></div>';
  t.classList.add('show');
  clearTimeout(t._timer);
  t._timer=setTimeout(function(){t.classList.remove('show');},3000);
}

function _showAchToast(title){
  showToast('🏆 '+title);
}

// ══════════════════════════════════════════════
//  AGENTS RENDER
// ══════════════════════════════════════════════
function _agentCard(a,isDesktopMode){
  var isKids=a.type==='kids';
  var lang=window._curLang||'ru';
  var role=lang==='kk'&&a.role_kk?a.role_kk:(a.role||a.description||'');
  var greet=lang==='kk'&&a.greeting_kk?a.greeting_kk:(a.greeting||'Привет!');
  var greetSafe=greet.replace(/\\/g,'\\\\').replace(/'/g,"\\'");
  var badge=isKids?tr('KIDS'):tr('ADULTS');
  var ava=getBotAvatar(a.customId?'custom_'+a.customId:a.id);

  // Аватар: фото или эмодзи/иконка
  var avaHtml=ava
    ?'<div class="av-desk" style="background:'+a.bg+';background-image:url('+ava+');background-size:cover;background-position:center"><span class="odot"></span></div>'
    :a.emoji
      ?'<div class="av-desk" style="background:'+a.bg+'"><span style="font-size:28px">'+a.emoji+'</span><span class="odot"></span></div>'
      :'<div class="av-desk" style="background:'+a.bg+'"><i class="'+a.icon+'" style="font-size:30px;color:rgba(0,0,0,.5)"></i><span class="odot"></span></div>';

  var avaMob=ava
    ?'<div class="av" style="background:'+a.bg+';background-image:url('+ava+');background-size:cover;background-position:center"><span class="odot"></span></div>'
    :a.emoji
      ?'<div class="av" style="background:'+a.bg+'"><span style="font-size:24px">'+a.emoji+'</span><span class="odot"></span></div>'
      :'<div class="av" style="background:'+a.bg+'"><i class="'+a.icon+'" style="font-size:26px;color:rgba(0,0,0,.5)"></i><span class="odot"></span></div>';

  if(isDesktopMode){
    var callFn=a.customId
      ?"startCallDesk('"+a.name+"','"+a.icon+"','"+greetSafe+"','"+a.type+"',"+a.customId+")"
      :"startCallDesk('"+a.name+"','"+a.icon+"','"+greetSafe+"','"+a.type+"')";
    return '<div class="acard '+(isKids?'kids':'adults')+'" style="position:relative">'
      +'<div class="acard-top">'+avaHtml
      +'<span class="ab '+(isKids?'bk':'ba')+'">'+badge+'</span>'
      +(a.customId?'<span class="my-badge">✦ MY</span>':'')
      +'</div>'
      +'<div class="acard-name">'+a.name+'</div>'
      +'<div class="acard-role">'+role+'</div>'
      +'<button class="cbtn" onclick="'+callFn+'"><i class="ri-vidicon-line"></i> '+tr('video_call')+'</button>'
      +'</div>';
  } else {
    var callFn2=a.customId
      ?"startCall('"+a.name+"','"+a.icon+"','"+greetSafe+"','"+a.type+"','"+a.bg+"',"+a.customId+")"
      :"startCall('"+a.name+"','"+a.icon+"','"+greetSafe+"','"+a.type+"','"+a.bg+"')";
    return '<div class="acard '+(isKids?'kids':'adults')+'" data-cat="'+a.cat+'">'
      +'<span class="ab '+(isKids?'bk':'ba')+'">'+badge+'</span>'
      +avaMob
      +'<div class="an">'+a.name+'</div><div class="ar">'+role+'</div>'
      +'<button class="cbtn" onclick="'+callFn2+'"><i class="ri-vidicon-line"></i> '+tr('call_btn')+'</button>'
      +'</div>';
  }
}

function _getAllAgents(cat){
  var all=AGENTS.slice();
  (S.customAgents||[]).forEach(function(ca){
    all.push({id:'custom_'+ca.id,name:ca.name,icon:'ri-user-star-line',bg:ca.bg_color||'#e8f4fd',
      emoji:ca.emoji,role:ca.description,role_kk:ca.description,type:ca.category,cat:ca.category,
      greeting:S.uiLang==='kk'?'Сәлем! Мен '+ca.name+'!':'Привет! Я '+ca.name+'!',
      greeting_kk:'Сәлем! Мен '+ca.name+'!',customId:ca.id});
  });
  if(!cat||cat==='all') return all;
  if(cat==='my') return all.filter(function(a){return !!a.customId;});
  return all.filter(function(a){return a.cat&&a.cat.indexOf(cat)!==-1;});
}

function renderAgentsDesktop(cat){
  window._lastCat=cat||'all';
  var grid=document.getElementById('agents-grid-desk'); if(!grid) return;
  var list=_getAllAgents(window._lastCat);
  if(!list.length){grid.innerHTML='<div style="padding:40px;color:var(--muted);text-align:center">'+tr('create_empty')+'</div>';return;}
  var INIT=6;
  grid.innerHTML=list.slice(0,INIT).map(function(a){return _agentCard(a,true);}).join('');
  if(list.length>INIT){
    var btn=document.createElement('button');
    btn.className='show-more-btn';
    btn.setAttribute('data-i18n','show_more');
    btn.textContent='Показать ещё ('+(list.length-INIT)+')';
    btn.onclick=function(){
      btn.remove();
      var extra=list.slice(INIT).map(function(a){return _agentCard(a,true);}).join('');
      grid.insertAdjacentHTML('beforeend',extra);
    };
    grid.appendChild(btn);
  }
}
window.renderAgentsDesktop=renderAgentsDesktop;

function renderAgentsMobile(cat){
  window._lastCat=cat||'all';
  var grid=document.getElementById('agents-grid-mob'); if(!grid) return;
  var list=_getAllAgents(window._lastCat);
  var INIT=6;
  grid.innerHTML=list.slice(0,INIT).map(function(a){return _agentCard(a,false);}).join('');
  if(list.length>INIT){
    var btn=document.createElement('button');
    btn.className='show-more-btn';
    btn.textContent='Показать ещё ('+(list.length-INIT)+')';
    btn.onclick=function(){
      btn.remove();
      var extra=list.slice(INIT).map(function(a){return _agentCard(a,false);}).join('');
      grid.insertAdjacentHTML('beforeend',extra);
    };
    grid.appendChild(btn);
  }
}
window.renderAgentsMobile=renderAgentsMobile;

function filterA(cat,btn){
  document.querySelectorAll('.ftab').forEach(function(b){b.classList.remove('on');});
  btn.classList.add('on');
  if(isDesktop) renderAgentsDesktop(cat); else renderAgentsMobile(cat);
}

// ══════════════════════════════════════════════
//  CUSTOM AGENT
// ══════════════════════════════════════════════
var _newAgentState={name:'',emoji:'🤖',bg:'#e8f4fd',description:'',category:'adults',voice:'neutral'};

function selectEmoji(el,emoji){
  _newAgentState.emoji=emoji;
  document.querySelectorAll('.emoji-pick').forEach(function(e){e.classList.remove('selected');});
  el.classList.add('selected');
  var p=document.getElementById('preview-avatar'); if(p){p.textContent=emoji;p.style.backgroundImage='';}
}
function selectColor(el,color){
  _newAgentState.bg=color;
  document.querySelectorAll('.color-dot').forEach(function(e){e.classList.remove('selected');});
  el.classList.add('selected');
  var p=document.getElementById('preview-avatar'); if(p) p.style.background=color;
}
function selectVoice(el,voice){
  _newAgentState.voice=voice;
  document.querySelectorAll('.voice-btn').forEach(function(e){e.classList.remove('selected');});
  el.classList.add('selected');
}
function selectCat(el,cat){
  _newAgentState.category=cat;
  document.querySelectorAll('.cat-btn').forEach(function(e){e.classList.remove('selected');});
  el.classList.add('selected');
}
function updatePreview(){
  var nm=document.getElementById('ca-name'); var desc=document.getElementById('ca-desc');
  var pn=document.getElementById('preview-name'); var pd=document.getElementById('preview-desc');
  if(nm&&pn){pn.textContent=nm.value||tr('create_name');_newAgentState.name=nm.value;}
  if(desc&&pd){pd.textContent=desc.value?desc.value.slice(0,70)+'...':tr('create_desc_hint');_newAgentState.description=desc.value;}
}

async function createCustomAgent(){
  var name=(document.getElementById('ca-name')||{}).value||'';
  var desc=(document.getElementById('ca-desc')||{}).value||'';
  if(!name.trim()){showToast(tr('err_fill_fields'),true);return;}
  if(!S.user.id){showToast('Войди сначала',true);return;}
  try{
    var r=await fetch('/api/agents/custom',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({user_id:S.user.id,name:name.trim(),emoji:_newAgentState.emoji,
        bg_color:_newAgentState.bg,description:desc,category:_newAgentState.category,voice_style:_newAgentState.voice})});
    var data=await r.json();
    if(data.ok){
      showToast(tr('create_success'));
      var ni=document.getElementById('ca-name'); if(ni) ni.value='';
      var di=document.getElementById('ca-desc'); if(di) di.value='';
      updatePreview();
      await loadCustomAgents(); loadMyAgents();
      addXP('custom_agent');
      renderAgentsDesktop(window._lastCat);
    } else { showToast('Ошибка создания',true); }
  }catch(e){showToast('Ошибка',true);}
}

async function loadCustomAgents(){
  if(!S.user.id) return;
  try{
    var r=await fetch('/api/agents/custom?user_id='+S.user.id);
    var d=await r.json(); if(d.ok) S.customAgents=d.agents;
  }catch(e){}
}

async function loadMyAgents(){
  await loadCustomAgents();
  var list=document.getElementById('my-agents-list'); if(!list) return;
  if(!S.customAgents||!S.customAgents.length){
    list.innerHTML='<div style="text-align:center;padding:24px;color:var(--muted);font-size:14px;">'+tr('create_empty')+'</div>';return;
  }
  list.innerHTML=S.customAgents.map(function(a){
    var ava=getBotAvatar('custom_'+a.id);
    var avaStyle=ava?'background-image:url('+ava+');background-size:cover;':'background:'+a.bg_color+';';
    return '<div class="my-agent-row">'
      +'<div class="my-agent-ava" style="'+avaStyle+'">'+(ava?'':a.emoji||'🤖')+'</div>'
      +'<div class="my-agent-info"><div class="my-agent-name">'+a.name+'</div>'
      +'<div class="my-agent-cat">'+(a.category==='kids'?tr('cat_kids'):tr('cat_adults'))+'</div></div>'
      +'<label class="my-agent-call" title="Загрузить фото" style="cursor:pointer">'
        +'<i class="ri-image-line"></i>'
        +'<input type="file" accept="image/*" style="display:none" onchange="uploadBotAvatar(this,\'custom_'+a.id+'\')">'
      +'</label>'
      +'<button class="my-agent-call" onclick="callCustomAgent('+a.id+',\''+a.name+'\')" title="'+tr('call_btn')+'"><i class="ri-vidicon-line"></i></button>'
      +'<button class="my-agent-del" onclick="deleteCustomAgent('+a.id+')" title="Удалить"><i class="ri-delete-bin-line"></i></button>'
      +'</div>';
  }).join('');
}

function callCustomAgent(id,name){
  var ca=S.customAgents.find(function(a){return a.id===id;}); if(!ca) return;
  var lang=window._curLang||'ru';
  var greet=lang==='kk'?'Сәлем! Мен '+ca.name+'! Танысқаныма қуаныштымын!':'Привет! Я '+ca.name+'. Рад познакомиться!';
  if(isDesktop) startCallDesk(ca.name,'ri-user-star-line',greet,ca.category,id);
  else startCall(ca.name,'ri-user-star-line',greet,ca.category,ca.bg_color||'#e8f4fd',id);
}

async function deleteCustomAgent(id){
  if(!confirm('Удалить персонажа?')) return;
  try{
    var r=await fetch('/api/agents/custom/'+id,{method:'DELETE'});
    var d=await r.json();
    if(d.ok){await loadCustomAgents();loadMyAgents();renderAgentsDesktop(window._lastCat);}
  }catch(e){}
}

// ══════════════════════════════════════════════
//  SETTINGS PAGE
// ══════════════════════════════════════════════
function initSettingsPage(){
  var nm=document.getElementById('set-name'); if(nm) nm.value=S.user.name||'';
  var av=document.getElementById('set-ava-preview');
  if(av){
    if(S.avatarUrl){av.style.backgroundImage='url('+S.avatarUrl+')';av.textContent='';}
    else{av.style.backgroundImage='';av.textContent=S.user.name?S.user.name[0].toUpperCase():'А';}
  }
  // Тоглы
  _setToggle('set-tog-tts',S.ttsOn);
  _setToggle('set-tog-speech',S.speechOn);
  _setToggle('set-tog-notif-bot',S.notifBotEnabled);
  _setToggle('set-tog-notif-streak',S.notifStreakEnabled);
  _setToggle('set-tog-notif-ach',S.notifAchEnabled);
  // Язык
  var ls=document.getElementById('set-lang-ui');
  if(ls) ls.value=window._curLang||'ru';
  var sl=document.getElementById('set-speech-lang');
  if(sl) sl.value=S.speechLang||'ru-RU';
  // Фото ботов
  _renderBotAvatarSettings();
}

function _setToggle(id,val){
  var el=document.getElementById(id); if(!el) return;
  el.checked=!!val;
}

function saveSettingsPage(){
  var nm=document.getElementById('set-name');
  if(nm&&nm.value.trim()){
    S.user.name=nm.value.trim();
    ['s-user-name-el','p-name','pch-name-el'].forEach(function(id){var e=document.getElementById(id);if(e)e.textContent=S.user.name;});
    _applyAvatarAll();
  }
  S.ttsOn=!!document.getElementById('set-tog-tts')&&document.getElementById('set-tog-tts').checked;
  S.speechOn=!!document.getElementById('set-tog-speech')&&document.getElementById('set-tog-speech').checked;
  S.notifBotEnabled=!!document.getElementById('set-tog-notif-bot')&&document.getElementById('set-tog-notif-bot').checked;
  S.notifStreakEnabled=!!document.getElementById('set-tog-notif-streak')&&document.getElementById('set-tog-notif-streak').checked;
  S.notifAchEnabled=!!document.getElementById('set-tog-notif-ach')&&document.getElementById('set-tog-notif-ach').checked;
  var ls=document.getElementById('set-lang-ui');
  if(ls&&ls.value) switchLang(ls.value);
  var sl=document.getElementById('set-speech-lang');
  if(sl&&sl.value){S.speechLang=sl.value;if(recognition)recognition.lang=sl.value;}
  saveSettings();
  showToast(tr('set_saved'));
}

function clearAllData(){
  if(!confirm(tr('set_clear_confirm'))) return;
  localStorage.clear();
  location.reload();
}

function _renderBotAvatarSettings(){
  var wrap=document.getElementById('set-bot-avatars'); if(!wrap) return;
  var lang=window._curLang||'ru';
  wrap.innerHTML=AGENTS.map(function(a){
    var ava=getBotAvatar(a.id);
    // Выбираем роль на нужном языке
    var role=lang==='kk'&&a.role_kk?a.role_kk:(a.role||a.description||'');
    return '<div class="set-bot-ava-row">'
      +'<div class="set-bot-ava-img" style="'+(ava?'background-image:url('+ava+');background-size:cover':'background:'+a.bg)+'">'
        +(ava?'':'<i class="'+a.icon+'" style="font-size:18px;color:#fff"></i>')
      +'</div>'
      +'<div style="flex:1"><div style="font-weight:600;font-size:13px">'+a.name+'</div>'
      +'<div style="font-size:11px;color:var(--muted)">'+role+'</div></div>'
      +'<label class="set-bot-upload-btn">'
        +'<i class="ri-image-add-line"></i>'
        +(ava?'<button onclick="clearBotAvatar(\''+a.id+'\',event)" class="clear-ava-btn">✕</button>':'')
        +'<input type="file" accept="image/*" style="display:none" onchange="uploadBotAvatar(this,\''+a.id+'\')">'
      +'</label>'
      +'</div>';
  }).join('');
}

function clearBotAvatar(id,e){
  e&&e.preventDefault&&e.preventDefault();
  localStorage.removeItem('vivlos_bot_ava_'+id);
  _renderBotAvatarSettings();
  renderAgentsDesktop(window._lastCat);
}

// ══════════════════════════════════════════════
//  LOGIN
// ══════════════════════════════════════════════
function swTab(t){
  document.getElementById('tin').className='tsb'+(t==='in'?' on':'');
  document.getElementById('treg').className='tsb'+(t==='reg'?' on':'');
  document.getElementById('f-login').style.display=t==='in'?'block':'none';
  document.getElementById('f-reg').style.display=t==='reg'?'block':'none';
}
function selAge(a){
  S.user.age=a;
  document.getElementById('ca').className='age-chip'+(a==='adult'?' sel':'');
  document.getElementById('ck').className='age-chip'+(a==='kid'?' sel':'');
}

function enterApp(){
  _applyAvatarAll();
  ['greet','dh-greet'].forEach(function(id){var el=document.getElementById(id);if(el)el.textContent='Привет, '+S.user.name+'! 👋';});
  ['s-user-name-el','p-name','pch-name-el'].forEach(function(id){var el=document.getElementById(id);if(el)el.textContent=S.user.name;});
  ['s-user-email-el','p-email','pch-email-el'].forEach(function(id){var el=document.getElementById(id);if(el)el.textContent=S.user.email;});
  updateStats();
  loadCustomAgents().then(function(){
    if(isDesktop){
      renderAgentsDesktop('all');
      document.getElementById('login-desk-screen').style.display='none';
      document.getElementById('app-desk').style.display='flex';
      dNavTo('home');
    } else {
      renderAgentsMobile('all'); navTo('home');
    }
  });
  _renderXPBar(); _renderStreak();
  setTimeout(_checkBotPush,30000);
}

function doLogout(){
  if(!confirm('Выйти из аккаунта?')) return;
  if(isDesktop){
    document.getElementById('app-desk').style.display='none';
    document.getElementById('login-desk-screen').style.display='flex';
  } else {
    document.querySelectorAll('.screen').forEach(function(s){s.classList.remove('active');});
    document.getElementById('s-login').classList.add('active');
    var bn=document.getElementById('bottom-nav'); if(bn) bn.className='bottom-nav';
  }
}

// ══════════════════════════════════════════════
//  BOT PUSH
// ══════════════════════════════════════════════
async function _checkBotPush(){
  if(!S.user.id||!S.notifBotEnabled) return;
  var bots=['ari','appa','bibo','nura','drako'];
  var bot=bots[Math.floor(Math.random()*bots.length)];
  var triggers=['miss','daily'];
  var trigger=triggers[Math.floor(Math.random()*triggers.length)];
  try{
    var r=await fetch('/api/notifications/bot-push',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({user_id:S.user.id,agent_id:bot,trigger:trigger,lang:window._curLang||'ru'})});
    var d=await r.json();
    if(d.ok&&!d.skipped){
      var badge=document.getElementById('notif-dot');
      if(badge){var c=parseInt(badge.textContent||'0');badge.textContent=c+1;badge.style.display='';}
      var hb=document.getElementById('dh-notif-dot'); if(hb) hb.style.display='';
    }
  }catch(e){}
  setTimeout(_checkBotPush,25*60*1000);
}

// ══════════════════════════════════════════════
//  NOTIFICATIONS
// ══════════════════════════════════════════════
var BOT_EMOJIS={ari:'🦊',bibo:'🤖',appa:'💜',max:'💪',drako:'🐉',lex:'🌍',
                zara:'🎨',altay:'🏔️',dina:'🩺',tim:'📈',nura:'🌸',kod:'💻',lou:'🌟'};

async function loadNotifications(){
  var listEl=document.getElementById('notif-list'); if(!listEl) return;
  var lang=window._curLang||'ru';
  listEl.innerHTML='<div class="notif-empty">'+tr('notif_loading')+'</div>';
  try{
    var uid=S.user.id||(window.USER_ID)||'';
    var url='/api/notifications?lang='+lang+(uid?'&user_id='+uid:'');
    var res=await fetch(url); var data=await res.json();
    if(!data.ok||!data.items||!data.items.length){
      listEl.innerHTML='<div class="notif-empty">'+tr('notif_empty')+'</div>'; return;
    }
    listEl.innerHTML=data.items.map(function(n){
      var kindCls='badge-'+(n.kind==='bot'?'bot':n.kind==='streak'?'streak':n.kind==='achievement'?'achievement':'info');
      var kindLabel=tr('kind_'+(n.kind||'info'));
      var avatar=n.kind==='bot'&&n.agent_id
        ?'<div class="notif-bot-avatar">'+(BOT_EMOJIS[n.agent_id]||'🤖')+'</div>'
        :'<div class="notif-ico"><i class="'+n.icon+'"></i></div>';
      return '<div class="notif-item'+(n.is_read?'':' unread')+(n.kind==='bot'&&!n.is_read?' bot-new':'')+'" data-id="'+n.id+'" onclick="markRead('+n.id+')">'
        +avatar+'<div class="notif-body"><span class="notif-kind-badge '+kindCls+'">'+kindLabel+'</span>'
        +'<div class="notif-title">'+n.title+'</div><div class="notif-msg">'+(n.body||'')+'</div>'
        +'<div class="notif-time">'+n.time+'</div></div>'+(n.is_read?'':'<div class="notif-unread-dot"></div>')+'</div>';
    }).join('');
    var unread=data.items.filter(function(n){return!n.is_read;}).length;
    var badge=document.getElementById('notif-dot');
    if(badge){badge.textContent=unread;badge.style.display=unread?'':'none';}
    var hd=document.getElementById('dh-notif-dot'); if(hd) hd.style.display=unread?'':'none';
  }catch(e){listEl.innerHTML='<div class="notif-empty">'+tr('notif_error')+'</div>';}
}
window.loadNotifications=loadNotifications;

async function markRead(nid){
  try{
    await fetch('/api/notifications/'+nid+'/read',{method:'POST'});
    var item=document.querySelector('[data-id="'+nid+'"]');
    if(item){item.classList.remove('unread','bot-new');var d=item.querySelector('.notif-unread-dot');if(d)d.remove();}
  }catch(e){}
}
window.markRead=markRead;

async function markAllRead(){
  try{await fetch('/api/notifications/read-all',{method:'POST'});loadNotifications();}catch(e){}
}
window.markAllRead=markAllRead;

// ══════════════════════════════════════════════
//  MOOD / STATS / ACHIEVEMENTS
// ══════════════════════════════════════════════
function pickMood(btn,mood){
  document.querySelectorAll('.mood-btn').forEach(function(b){b.classList.remove('picked');});
  btn.classList.add('picked'); S.mood=mood;
}

function updateStats(){
  var mins=Math.round(S.totalSecs/60);
  var map=[['stat-calls','calls'],['stat-mins','mins'],['stat-streak','streak'],['stat-ach','achievements'],
           ['ds-calls','calls'],['ds-mins','mins'],['ds-streak','streak'],['ds-ach','achievements']];
  map.forEach(function(p){
    var el=document.getElementById(p[0]); if(!el) return;
    el.textContent=p[1]==='mins'?mins:S[p[1]]!==undefined?S[p[1]]:0;
  });
  ['streak-n','ds-streak-pill'].forEach(function(id){var el=document.getElementById(id);if(el)el.textContent=S.streak;});
}

function updateProfileUI(){
  var mins=Math.round(S.totalSecs/60);
  _applyAvatarAll();
  ['p-name','pch-name-el'].forEach(function(id){var el=document.getElementById(id);if(el)el.textContent=S.user.name;});
  ['p-email','pch-email-el'].forEach(function(id){var el=document.getElementById(id);if(el)el.textContent=S.user.email;});
  ['p-type','pch-type-el'].forEach(function(id){var el=document.getElementById(id);if(el)el.textContent=S.user.age==='adult'?'👤 '+tr('adult'):'🧒 '+tr('kid');});
  ['ps-calls','dps-calls'].forEach(function(id){var el=document.getElementById(id);if(el)el.textContent=S.calls;});
  ['ps-mins','dps-mins'].forEach(function(id){var el=document.getElementById(id);if(el)el.textContent=mins;});
  ['ps-streak','dps-streak'].forEach(function(id){var el=document.getElementById(id);if(el)el.textContent=S.streak;});
  _renderXPBar(); _renderStreak(); updateAchievements();
}

function updateAchievements(){
  var achList=document.querySelectorAll('.ach-item'); if(!achList.length) return;
  var conditions=[
    S.calls>=1, S.streak>=7, S.calls>=10, S.totalSecs>=3600,
    S.calls>=5&&S.totalSecs>=1500, S.calls>=3, S.history.length>=3, S.calls>=20,
    (S.customAgents&&S.customAgents.length>=1), S.streak>=30
  ];
  var earned=0;
  conditions.forEach(function(unlocked,i){
    if(!achList[i]) return;
    var wasLocked=achList[i].classList.contains('locked');
    if(unlocked){
      achList[i].classList.add('earned'); achList[i].classList.remove('locked'); earned++;
      if(wasLocked){
        var nm=achList[i].querySelector('.ach-name');
        if(nm) setTimeout(function(){_showAchToast(nm.textContent);},200);
        addXP('achievement');
      }
    } else {
      achList[i].classList.add('locked'); achList[i].classList.remove('earned');
    }
  });
  S.achievements=earned;
  var el=document.getElementById('ds-ach'); if(el) el.textContent=earned;
}

// ══════════════════════════════════════════════
//  HISTORY
// ══════════════════════════════════════════════
function renderHistory(){
  ['hist-list','hist-list-desk'].forEach(function(elId){
    var el=document.getElementById(elId); if(!el) return;
    if(!S.history.length){
      el.innerHTML=elId==='hist-list-desk'
        ?'<div class="hist-empty-desk"><i class="ri-phone-line"></i><p>'+tr('hist_empty')+'</p></div>'
        :'<div class="hist-empty"><div class="he">📞</div><p>'+tr('hist_empty')+'</p></div>';
      return;
    }
    if(elId==='hist-list-desk'){
      el.innerHTML=S.history.map(function(h){
        return '<div class="hist-row">'
          +'<div class="hist-row-agent"><div class="hist-row-ava" style="background:'+h.bg+'"><i class="'+h.icon+'"></i></div><div class="hist-row-name">'+h.name+'</div></div>'
          +'<div class="hist-row-preview">'+h.preview+'</div>'
          +'<div class="hist-row-time">'+h.time+'</div>'
          +'<div class="hist-row-dur">'+h.dur+'</div></div>';
      }).join('');
    } else {
      el.innerHTML=S.history.map(function(h){
        return '<div class="hist-item"><div class="hist-ava" style="background:'+h.bg+'"><i class="'+h.icon+'"></i></div>'
          +'<div class="hist-info"><div class="hist-name">'+h.name+'</div><div class="hist-preview">'+h.preview+'</div></div>'
          +'<div class="hist-meta"><div class="hist-time">'+h.time+'</div><div class="hist-dur">'+h.dur+'</div></div></div>';
      }).join('');
    }
  });
}

// ══════════════════════════════════════════════
//  CALL
// ══════════════════════════════════════════════
function startCall(name,icon,greeting,type,bg,customId){
  var found=AGENTS.find(function(a){return a.name===name;});
  agent={id:found?found.id:name.toLowerCase(),name:name,icon:icon,greeting:greeting,type:type,bg:bg||'#fff3d9',customId:customId||null};
  chatHistory=[{role:'assistant',content:greeting}];
  var el;
  el=document.getElementById('c-title');if(el)el.textContent=name;
  el=document.getElementById('c-name');if(el)el.textContent=name;
  var orbEl=document.getElementById('c-emoji');if(orbEl)orbEl.innerHTML='<i class="'+icon+'"></i>';
  el=document.getElementById('c-status');if(el)el.textContent='● Онлайн';
  el=document.getElementById('c-chat');if(el)el.innerHTML='';
  _addBubbleRich('ai',greeting,'c-chat');
  secs=0;clearInterval(timer);
  timer=setInterval(function(){secs++;var m=Math.floor(secs/60),s=secs%60;
    var tel=document.getElementById('c-timer');if(tel)tel.textContent=(m<10?'0':'')+m+':'+(s<10?'0':'')+s;},1000);
  navTo('call');initSpeech('c-chat');
}

function startCallDesk(name,icon,greeting,type,customId){
  var found=AGENTS.find(function(a){return a.name===name;});
  agent={id:found?found.id:name.toLowerCase(),name:name,icon:icon,greeting:greeting,type:type,customId:customId||null};
  chatHistory=[{role:'assistant',content:greeting}];
  var el;
  el=document.getElementById('dc-title');if(el)el.textContent=name;
  el=document.getElementById('dc-name');if(el)el.textContent=name;
  var orbEl=document.getElementById('dc-emoji');if(orbEl)orbEl.innerHTML='<i class="'+icon+'"></i>';
  el=document.getElementById('dc-status');if(el)el.textContent='● Онлайн';
  el=document.getElementById('dc-chat');if(el)el.innerHTML='';
  _addBubbleRich('ai',greeting,'dc-chat');
  secs=0;clearInterval(timer);
  timer=setInterval(function(){secs++;var m=Math.floor(secs/60),s=secs%60;
    var tel=document.getElementById('dc-timer');if(tel)tel.textContent=(m<10?'0':'')+m+':'+(s<10?'0':'')+s;},1000);
  var overlay=document.getElementById('call-overlay');if(overlay)overlay.classList.add('active');
  initSpeech('dc-chat');
}
window.startCallDesk=startCallDesk;

function endCall(){
  // Stop all audio
  clearInterval(timer);
  stopListening();
  // Stop realtime loop if active
  if(typeof stopRealtimeLoop === 'function') stopRealtimeLoop();
  // Stop TTS
  if(window.speechSynthesis) window.speechSynthesis.cancel();
  if(window._ttsAudio){ window._ttsAudio.pause(); window._ttsAudio=null; }
  // Stop camera
  if(window.combinedStream){ window.combinedStream.getTracks().forEach(function(t){t.stop();}); }
  if(window._dfInterval){ clearInterval(window._dfInterval); window._dfInterval=null; }

  S.totalSecs+=secs; S.calls++;
  addXP('per_minute',Math.max(1,Math.floor(secs/60))*2);
  var m=Math.floor(secs/60),s=secs%60;
  var durStr=(m>0?m+'мин ':'')+s+'с';
  var now=new Date();var timeStr=now.getHours()+':'+String(now.getMinutes()).padStart(2,'0');
  var last=chatHistory[chatHistory.length-1];
  var preview=chatHistory.length>2?(last?last.content.slice(0,50)+'...':'—'):'—';
  S.history.unshift({name:agent.name,icon:agent.icon,bg:agent.bg||'#fff3d9',preview:preview,time:timeStr,dur:durStr});
  updateStats();

  // 1. Hide overlay FIRST (before stopping camera — avoids black flash)
  var overlay=document.getElementById('call-overlay');
  if(overlay){
    overlay.classList.remove('active');
    overlay.style.display='none';
  }

  // 2. Navigate to home on ALL devices
  navTo('home');

  // 3. Stop camera/mic AFTER navigation (no black screen flash)
  setTimeout(function(){
    if(window.combinedStream){
      window.combinedStream.getTracks().forEach(function(t){ t.stop(); });
      window.combinedStream = null;
    }
    if(window._dfInterval){ clearInterval(window._dfInterval); window._dfInterval=null; }
    if(typeof stopRealtimeLoop==='function') stopRealtimeLoop();
  }, 100);

  updateAchievements();
  // Reset state
  aiThinking=false; window._speechInProgress=false; secs=0;
}

function clearChat(){
  var chatId=isDesktop?'dc-chat':'c-chat';
  var el=document.getElementById(chatId);if(el)el.innerHTML='';chatHistory=[];
}
function toggleMic(){
  micOn=!micOn;
  document.querySelectorAll('#mic-btn,#mic-btn-desk').forEach(function(b){
    b.innerHTML=micOn?'<i class="ri-mic-line"></i>':'<i class="ri-mic-off-line"></i>';
    b.className='ctrl'+(micOn?'':' muted');
  });
  micOn?startListening():stopListening();
}
function toggleCam(){
  camOn=!camOn;
  if(window.combinedStream) window.combinedStream.getVideoTracks().forEach(function(t){t.enabled=camOn;});
  var vid=document.getElementById('user-cam');if(vid)vid.style.visibility=camOn?'visible':'hidden';
  document.querySelectorAll('#cam-btn,#cam-btn-desk').forEach(function(b){
    b.innerHTML=camOn?'<i class="ri-vidicon-line"></i>':'<i class="ri-vidicon-off-line"></i>';
    b.className='ctrl'+(camOn?'':' muted');
  });
}

// ══════════════════════════════════════════════
//  SPEECH / AI
// ══════════════════════════════════════════════
var activeChatId='c-chat';
window._lastUserSpokeTs=Date.now();
window._lastAiRespondedTs=0;

function initSpeech(chatId){
  activeChatId=chatId||'c-chat';setVS('loading','Загрузка...');useWebSpeech();
}

var _silenceTimer = null;
var _pendingTranscript = '';
function useWebSpeech(){
  var SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){setVS('error','Используйте Chrome или Edge');return;}
  if(!window.combinedStream||!window.combinedStream.active){
    setVS('loading','Жду камеру...');setTimeout(useWebSpeech,500);return;
  }
  recognition=new SR();
  // Язык берём из выбранного в звонке (_callLang) или UI (_curLang)
  var lang = window._callLang || window._curLang || 'ru';
  var _LANG_BCP = {ru:'ru-RU', kk:'kk-KZ', en:'en-US', de:'de-DE'};
  recognition.lang = _LANG_BCP[lang] || 'ru-RU';
  recognition.continuous = true;
  recognition.interimResults = true;
  // Казахский: увеличиваем паузу перед завершением — чтобы не обрывало
  recognition.maxAlternatives = 3;
  recognition.onstart=function(){isListening=true;
    setVS('listening', lang==='kk'?'Тыңдап тұрмын...':'Слушаю...');setWave(true);};
  recognition.onend = function() {
    isListening = false; setWave(false);
    clearTimeout(_silenceTimer);
    // Автоматически перезапускаем если микрофон включён
    if(micOn && !aiThinking) {
      setTimeout(function() {
        if(micOn && !isListening && !aiThinking) {
          try { recognition.start(); } catch(e) {}
        }
      }, 300);
    }
  };
  recognition.onerror=function(e){
    if(e.error==='not-allowed'||e.error==='audio-capture')
      setVS('error',lang==='kk'?'Микрофонға рұқсат беріңіз':'Разрешите доступ к микрофону');
    // На других ошибках просто перезапускаем
    if(e.error==='network'||e.error==='aborted'){
      setTimeout(function(){if(micOn&&!isAISpeaking)startListening();},1000);
    }
  };
  recognition.onresult=function(e){
    var interim='',finalTxt='';
    for(var i=e.resultIndex;i<e.results.length;i++){
      if(e.results[i].isFinal) finalTxt+=e.results[i][0].transcript;
      else interim+=e.results[i][0].transcript;
    }
    if(interim){
      setTLive('🎙 '+interim+'...');
      window._pendingTranscript=interim;
      clearTimeout(window._silenceTimer);
      // KK нужно 3+ секунды — длинные слова и частые паузы внутри фраз
      var _ms = window._callLang==='kk' ? 3500
               : window._callLang==='de' ? 2800
               : 2000; // ru/en тоже увеличили с 1500 до 2000
      window._silenceTimer=setTimeout(function(){
        if(window._pendingTranscript&&micOn&&!isAISpeaking&&!aiThinking&&Date.now()>ignoreUntil){
          handleSpeech(window._pendingTranscript.trim());
          window._pendingTranscript='';
        }
      },_ms);
    }
    if(finalTxt.trim()&&micOn&&!isAISpeaking&&Date.now()>ignoreUntil&&(Date.now()-lastAISpeechTime>2000)){
      clearTimeout(window._silenceTimer);
      window._pendingTranscript='';
      setTLive('✅ '+finalTxt.trim());
      handleSpeech(finalTxt.trim());
    }
  };
  voskReady=true;
  setVS('ready', lang==='kk'?'Дайын — сөйлеңіз!':'Готов — говорите!');
  startListening();
}

function startListening(){if(!voskReady||!recognition||isListening||!micOn||isAISpeaking)return;try{recognition.start();}catch(e){}}
function stopListening(){if(recognition&&isListening){try{recognition.stop();}catch(e){}}setWave(false);}
function setVS(state,label){document.querySelectorAll('#v-dot,#dv-dot').forEach(function(el){el.className='vdot '+state;});document.querySelectorAll('#v-label,#dv-label').forEach(function(el){el.textContent=label;});}
function setWave(on){document.querySelectorAll('#wviz,#dwviz').forEach(function(el){el.className='wviz'+(on?' on':'');});}
function setTLive(txt){document.querySelectorAll('#t-live,#dt-live').forEach(function(el){el.textContent=txt;});}

var _lastFb=-1;
function fallback(){
  var r=['Расскажи подробнее!','Хм, и что дальше?','Как ты к этому пришёл?','А что ты думаешь?',
         'Интересно! Продолжай...','Ого, серьёзно?','Что ты сам чувствуешь?','Как это на тебя влияет?'];
  var idx;do{idx=Math.floor(Math.random()*r.length);}while(idx===_lastFb&&r.length>1);
  _lastFb=idx;return r[idx];
}


// Client-side language detector — mirrors server-side _detect_lang
function _detectLangClient(text) {
  if(!text || text.trim().length < 3) return null;
  // Kazakh — special chars (absolute priority)
  if(/[әіңғүұқөһӘІҢҒҮҰҚӨҺ]/.test(text)) return 'kk';
  var cyrillic = (text.match(/[а-яёА-ЯЁ]/g)||[]).length;
  var latin    = (text.match(/[a-zA-Z]/g)||[]).length;
  if(cyrillic > latin) return 'ru';
  if(latin < 2) return 'ru';
  // German
  if(/[äöüÄÖÜß]/.test(text)) return 'de';
  var words = text.toLowerCase().split(/\s+/);
  var de = new Set(['ich','du','ist','bin','hast','haben','wie','was','guten','danke',
                    'bitte','ja','nein','nicht','und','der','die','das','für','hallo',
                    'geht','gut','schön','mir','dir','auch','noch','wir','sie']);
  if(words.filter(function(w){return de.has(w);}).length >= 2) return 'de';
  return 'en';
}

// ══ Языковая память — фиксируем казахский после 3 сообщений ══
var _langMessageCount = { kk:0, ru:0, en:0, de:0 };
var _langLocked = null;  // null = авто, 'kk'/'ru' = зафиксирован

function trackLangPreference(detectedLang) {
  if(!detectedLang || detectedLang === 'neutral') return;
  _langMessageCount[detectedLang] = (_langMessageCount[detectedLang]||0) + 1;

  // После 3 сообщений подряд на одном языке — фиксируем
  var dominant = Object.keys(_langMessageCount).reduce(function(a,b){
    return _langMessageCount[a]>_langMessageCount[b]?a:b;
  });
  if(_langMessageCount[dominant] >= 3 && dominant !== _langLocked) {
    _langLocked = dominant;
    window._callLang = dominant;
    // Обновляем флаг в UI
    var flags = {ru:'🇷🇺',kk:'🇰🇿',en:'🇬🇧',de:'🇩🇪'};
    var codes  = {ru:'RU',kk:'KZ',en:'EN',de:'DE'};
    var fl = document.getElementById('call-lang-flag');
    if(fl) fl.textContent = flags[dominant]||'🌐';
    var cd = document.getElementById('call-lang-code');
    if(cd) cd.textContent = codes[dominant]||dominant.toUpperCase();
    console.log('🔒 Language locked to:', dominant);
    // Сохраняем на сервере
    fetch('/api/lang/set',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({lang:dominant})}).catch(function(){});
    // Перезапускаем recognition с правильным языком
    if(window.recognition) {
      var bcp={ru:'ru-RU',kk:'kk-KZ',en:'en-US',de:'de-DE'};
      window.recognition.lang = bcp[dominant]||'ru-RU';
      if(window.isListening){ try{window.recognition.stop();}catch(e){} }
    }
  }
}
async function handleSpeech(text){
  if(aiThinking||!text||!text.trim()) return;
  aiThinking=true;
  window._lastUserSpokeTs=Date.now();

  // Force reset after 25 sec
  var _aiHangTimer=setTimeout(function(){
    if(aiThinking){
      aiThinking=false; window._speechInProgress=false;
      setStatus('● Онлайн'); orbSpeak(false);
      console.warn('⚠️ aiThinking timeout — force reset');
    }
  }, 25000);

  _addBubbleRich('user', text, activeChatId);
  chatHistory.push({role:'user', content:text});

  // Auto-detect language from typed text
  var _detectedLang = _langLocked || _detectLangClient(text);
  if(_detectedLang && !_langLocked) {
    window._callLang = _detectedLang;
    fetch('/api/lang/set', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({lang: _detectedLang})}).catch(function(){});
  }
  // Track for language memory
  if(_detectedLang) trackLangPreference(_detectedLang);

  var thinkEl = _addThinkingBubble(activeChatId);
  setStatus('● Думает...'); orbSpeak(false);

  try {
    // ── Try STREAMING first ──────────────────────────────
    var streamed = await _streamReply(text, thinkEl);
    if(!streamed) {
      // ── Fallback to regular /api/chat ───────────────────
      var r = await fetch('/api/chat', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({
          messages: chatHistory.slice(-8),
          agent: agent.id||'ari',
          custom_agent_id: agent.customId||null,
          emotion: window.lastEmotion||'neutral',
          emotion_confidence: window.emotionConfidence||0,
          face_data: window.faceData||{},
          lang: window._callLang||window._curLang||'ru',
          user_name: S.user.name||'', user_age: S.user.age||'adult'
        })
      });
      var data = await r.json();
      var reply = (data.ok&&data.reply) ? data.reply : fallback();
      thinkEl.remove();
      _addBubbleRich('ai', reply, activeChatId);
      chatHistory.push({role:'assistant', content:reply});
      window._lastAiRespondedTs=Date.now();
      setStatus('● Говорит...'); orbSpeak(true);
      speak(reply);
    }
  } catch(e) {
    console.warn('handleSpeech error:', e);
    thinkEl.remove();
    var fb = fallback();
    _addBubbleRich('ai', fb, activeChatId);
    chatHistory.push({role:'assistant', content:fb});
    setStatus('● Онлайн'); orbSpeak(false);
    aiThinking=false; window._speechInProgress=false;
    if(micOn) startListening();
  } finally {
    clearTimeout(_aiHangTimer);
  }
}

// ══ Streaming reply — token by token ══════════════════════
async function _streamReply(text, thinkEl) {
  try {
    var lang = window._callLang||window._curLang||'ru';
    var agentId = agent.id||'ari';

    var resp = await fetch('/api/chat/stream', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        message: text,
        messages: chatHistory.slice(-8),
        agent_id: agentId,
        lang: lang,
        emotion: window.lastEmotion||'neutral',
        face_data: window.faceData||{},
      })
    });

    if(!resp.ok || !resp.body) return false;

    // Show streaming bubble
    thinkEl.remove();
    var streamDiv = document.createElement('div');
    streamDiv.className = 'bubble ai streaming';
    streamDiv.innerHTML = '<div class="stream-text"></div><div class="bubble-time">'+_nowTime()+'</div>';
    var ch = document.getElementById(activeChatId);
    if(ch) ch.appendChild(streamDiv);

    var textDiv = streamDiv.querySelector('.stream-text');
    var reader = resp.body.getReader();
    var decoder = new TextDecoder();
    var fullText = '';
    var buffer = '';

    while(true) {
      var _r = await reader.read();
      if(_r.done) break;
      buffer += decoder.decode(_r.value, {stream:true});
      var lines = buffer.split('\n');
      buffer = lines.pop();

      for(var line of lines) {
        if(!line.startsWith('data: ')) continue;
        var raw = line.slice(6).trim();
        if(raw === '[DONE]') break;
        try {
          var d = JSON.parse(raw);
          if(d.token) {
            fullText += d.token;
            textDiv.textContent = fullText;
            if(ch) ch.scrollTop = ch.scrollHeight;
          }
        } catch(e) {}
      }
    }

    streamDiv.classList.remove('streaming');
    if(fullText.trim()) {
      chatHistory.push({role:'assistant', content:fullText.trim()});
      window._lastAiRespondedTs = Date.now();
      setStatus('● Говорит...'); orbSpeak(true);
      speak(fullText.trim());
      return true;
    }
    streamDiv.remove();
    return false;

  } catch(e) {
    console.warn('_streamReply error:', e);
    return false;
  }
}

function setStatus(txt){document.querySelectorAll('#c-status,#dc-status').forEach(function(el){el.textContent=txt;});}

// Реакции ИИ на эмоции — уникальные для каждого персонажа
var _EMOTION_TRIGGERS = {
  ru: {
    // Серьёзные — реагировать быстро
    sad:       ['что-то случилось?', 'вижу, нелегко... хочешь рассказать?', 'я здесь, что-то не так?', 'расскажи, что произошло?'],
    angry:     ['что-то выбесило?', 'слышу напряжение — что случилось?', 'что тебя раздражает?'],
    fearful:   ['всё в порядке?', 'кажется, что-то беспокоит...', 'что-то тревожит?'],
    // Позитивные — поддержать и расспросить
    happy:     ['вижу, хорошее настроение! что случилось?', 'что-то радостное произошло?', 'как прошёл день?', 'поделишься что хорошего?'],
    excited:   ['ого, что-то крутое случилось?', 'вижу восторг! расскажи!', 'что произошло — рассказывай!'],
    surprised: ['ого, что-то удивило?', 'что-то неожиданное?', 'расскажи что случилось!'],
    // Состояния — участливо реагировать
    tired:     ['выглядишь усталым... как ты?', 'тяжёлый день был?', 'когда последний раз отдыхал нормально?'],
    nervous:   ['кажется, ты нервничаешь... всё ок?', 'что-то беспокоит?', 'хочешь поговорить о чём-то?'],
    focused:   ['вижу, ты сосредоточен... чем занимаешься?', 'что-то важное делаешь?'],
    bored:     ['скучаешь?', 'может придумаем что-нибудь интересное?', 'чем бы хотел заняться?'],
    confused:  ['что-то непонятно?', 'заметил растерянность — помочь разобраться?'],
    pensive:   ['о чём думаешь?', 'задумался... поделишься?', 'что-то на уме?'],
    contempt:  ['что-то не устраивает?', 'вижу скептицизм — что думаешь?'],
    disgusted: ['что-то не нравится?', 'что случилось?'],
    neutral:   ['как дела?', 'как прошёл день?', 'о чём думаешь?'],
  },
  kk: {
    sad:       ['не болды?', 'жақсы емес сияқтысың... айтып берші?', 'мен осындамын, не болды?'],
    angry:     ['бір нәрсе ашуландырды ма?', 'не болды, айтып бер?'],
    fearful:   ['бәрі жақсы ма?', 'бірдеңе мазалап тұр ма?'],
    happy:     ['көңіл-күйің жақсы! не болды?', 'бір қуанышты нәрсе болды ма?', 'күнің қалай өтті?'],
    excited:   ['ого, не болды?', 'қуанышты нәрсе болды ма, айтшы!'],
    surprised: ['уа, не болды?', 'таңданттырды ма бірдеңе?'],
    tired:     ['шаршаған сияқтысың... қалайсың?', 'ауыр күн болды ма?'],
    nervous:   ['алаңдап тұрсың ба?', 'бірдеңе мазалайды ма?'],
    focused:   ['не істеп жатырсың?', 'маңызды нәрсе жасап жатырсың ба?'],
    bored:     ['зерігіп тұрсың ба?', 'бірдеңе қызықты ойлайық?'],
    pensive:   ['не ойлап отырсың?', 'бөлісесің бе?'],
    neutral:   ['қалайсың?', 'күнің қалай өтті?', 'не ойлап отырсың?'],
    disgusted: ['бір нәрсе ұнамады ма?'],
    confused:  ['бірдеңе түсініксіз бе? көмектесейін.'],
    contempt:  ['не ойлайсың?'],
  }
};

var _lastTriggerIdx = {};

async function triggerAIReaction(emotion, confidence, isCallStart) {
  if(window._speechInProgress) return;
  try {
    var lang = window._callLang || window._curLang || 'ru';
    var agentId = (window.agent && window.agent.id) || 'ari';

    var pool = (_EMOTION_TRIGGERS[lang] || _EMOTION_TRIGGERS.ru)[emotion];
    if(!pool || !pool.length) pool = (_EMOTION_TRIGGERS['ru'])[emotion] || ['как дела?'];

    var lastIdx = _lastTriggerIdx[emotion] || -1;
    var idx;
    do { idx = Math.floor(Math.random() * pool.length); }
    while (idx === lastIdx && pool.length > 1);
    _lastTriggerIdx[emotion] = idx;
    var triggerMsg = pool[idx];

    // При начале звонка — более тёплое, развёрнутое вступление
    if(isCallStart) {
      var userName = (S && S.user && S.user.name) ? S.user.name.split(' ')[0] : '';
      var greeting = {
        ru: { happy:'вижу, у тебя хорошее настроение', sad:'вижу, что-то не так', tired:'выглядишь уставшим', excited:'вижу огонь в глазах!', neutral:'рад тебя видеть', nervous:'кажется, ты немного напряжён', fearful:'кажется, что-то беспокоит' },
        kk: { happy:'көңіл-күйің жақсы екен', sad:'бірдеңе болды сияқты', tired:'шаршаған сияқтысың', excited:'қуанышты екенсің!', neutral:'көргенім қуантты', nervous:'бірдеңе мазалап тұр ма', fearful:'бірдеңеден алаңдап тұрсың' },
      };
      var g = (greeting[lang]||greeting['ru'])[emotion] || (greeting['ru'][emotion]||'');
      if(g) triggerMsg = (userName?userName+', ':'')+g+'... '+triggerMsg;
    }

    // Добавляем в историю как внутренний триггер
    var chatHist = (window.chatHistory || []).slice(-6);
    // Добавляем скрытый эмоциональный сигнал в последнее сообщение
    var messagesWithEmo = chatHist.length
      ? chatHist
      : [{role: 'user', content: '(молчит, ' + emotion + ')'}];

    var r = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        messages:        messagesWithEmo,
        agent:           agentId,
        custom_agent_id: (window.agent && window.agent.customId) || null,
        emotion:         emotion,
        emotion_confidence: Math.max(confidence || 0.5, 0.65),  // усиливаем уверенность
        face_data:       window.faceData || {},
        lang:            lang,
        user_name:       S.user.name || '',
        user_age:        S.user.age || 'adult',
        emotion_trigger: triggerMsg,  // подсказка AI о чём спросить
      })
    });
    var data = await r.json();
    if(data.ok && data.reply) {
      window._lastAiRespondedTs = Date.now();
      var chatId = isDesktop ? 'dc-chat' : 'c-chat';
      _addBubbleRich('ai', data.reply, chatId);
      chatHistory.push({role: 'assistant', content: data.reply});
      speak(data.reply);
    }
  } catch(e) { console.debug('triggerAIReaction error:', e); }
}

// Улучшенные пузыри
function _addBubbleRich(type,text,chatId){
  var ch=document.getElementById(chatId||'c-chat');if(!ch)return{remove:function(){}};
  var div=document.createElement('div');div.className='bubble '+type;
  div.innerHTML='<div>'+_esc(text)+'</div><div class="bubble-time">'+_nowTime()+'</div>';
  ch.appendChild(div);
  // Scroll to bottom smoothly
  requestAnimationFrame(function(){ ch.scrollTop = ch.scrollHeight; });
  return div;
}
function _addThinkingBubble(chatId){
  var ch=document.getElementById(chatId||'c-chat');if(!ch)return{remove:function(){}};
  var div=document.createElement('div');div.className='bubble thinking';
  div.innerHTML='<div class="typing-dots"><span></span><span></span><span></span></div>';
  ch.appendChild(div);ch.scrollTop=ch.scrollHeight;return div;
}
function addBubble(type,text,chatId){return _addBubbleRich(type,text,chatId);}
function _esc(t){return String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function _nowTime(){var d=new Date();return d.getHours()+':'+String(d.getMinutes()).padStart(2,'0');}

// TTS
function speak(text){
  if(!S.ttsOn){aiThinking=false;window._speechInProgress=false;if(micOn)setTimeout(startListening,500);return;}
  isAISpeaking=true;ignoreUntil=Date.now()+3500;stopListening();
  var safetyTimer=setTimeout(function(){
    if(isAISpeaking){isAISpeaking=false;aiThinking=false;lastAISpeechTime=Date.now();
      orbSpeak(false);setStatus('● Онлайн');if(micOn)startListening();}
  },12000);
  // Use _callLang if set (video call language), fall back to UI language
  var _ttsLang = window._callLang || window._curLang || 'ru';
  var _agentId = agent ? (agent.id || 'ari') : 'ari';
  var _customVoice = (agent && agent.customId) ? (agent.voice_style || 'neutral') : null;
  fetch('/api/tts',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({
      text:text, lang:_ttsLang,
      agent: _agentId,
      custom_voice: _customVoice
    })})
  .then(function(r){if(!r.ok)throw new Error('tts '+r.status);return r.blob();})
  .then(function(blob){
    var url=URL.createObjectURL(blob);var audio=new Audio(url);
    window._ttsAudio=audio; orbSpeak(true);
    audio.onended=function(){clearTimeout(safetyTimer);isAISpeaking=false;lastAISpeechTime=Date.now();
      orbSpeak(false);setStatus('● Онлайн');aiThinking=false;URL.revokeObjectURL(url);
      setTimeout(function(){if(micOn&&!isAISpeaking)startListening();},1500);};
    audio.onerror=audio.play().catch=function(){clearTimeout(safetyTimer);isAISpeaking=false;aiThinking=false;
      orbSpeak(false);setStatus('● Онлайн');if(micOn)startListening();};
    audio.play().catch(function(){clearTimeout(safetyTimer);isAISpeaking=false;aiThinking=false;
      orbSpeak(false);setStatus('● Онлайн');if(micOn)startListening();});
  })
  .catch(function(){clearTimeout(safetyTimer);isAISpeaking=false;aiThinking=false;
    orbSpeak(false);setStatus('● Онлайн');if(micOn)startListening();});
}

function orbSpeak(on){
  // Use classList.toggle — never reassign className (that resets CSS animations!)
  document.querySelectorAll('#ai-orb,#dai-orb').forEach(function(el){
    el.classList.toggle('speaking', !!on);
  });
  document.querySelectorAll('#r1,#dr1').forEach(function(el){
    el.classList.toggle('pulse', !!on);
  });
  document.querySelectorAll('#r2,#dr2').forEach(function(el){
    el.classList.toggle('pulse', !!on);
  });
}

function toggleSet(btn){
  var isOn=btn.classList.contains('on');btn.className='toggle '+(isOn?'off':'on');
  if(btn.id==='tog-tts')S.ttsOn=!isOn;
  if(btn.id==='tog-speech')S.speechOn=!isOn;
  saveSettings();
}
function changeLang(val){S.speechLang=val;if(recognition)recognition.lang=val;saveSettings();}

// ══════════════════════════════════════════════
//  ТЕМЫ
// ══════════════════════════════════════════════
var THEMES = [
  { id:'default', name:'Синий', name_kk:'Көк',    color:'#0ea5e9', emoji:'🌊' },
  { id:'galactic',name:'Галактика',name_kk:'Ғалам', color:'#a855f7', emoji:'🔮' },
  { id:'forest',  name:'Лес',    name_kk:'Орман',  color:'#10b981', emoji:'🌿' },
  { id:'sunset',  name:'Закат',  name_kk:'Күн батыс', color:'#f97316', emoji:'🌅' },
  { id:'sakura',  name:'Сакура', name_kk:'Сакура', color:'#ec4899', emoji:'🌸' },
  { id:'dark',    name:'Тёмный', name_kk:'Қараңғы', color:'#334155', emoji:'🌙' },
];

var _currentTheme = localStorage.getItem('vivlos_theme')||'default';

function applyTheme(id){
  THEMES.forEach(function(t){ document.body.classList.remove('theme-'+t.id); });
  if(id!=='default') document.body.classList.add('theme-'+id);
  _currentTheme=id;
  localStorage.setItem('vivlos_theme',id);
  localStorage.setItem('vivlos_login_theme',id); // синхронизируем с логином

  // Update swatches
  document.querySelectorAll('.theme-swatch').forEach(function(sw){
    sw.classList.toggle('active', sw.dataset.theme===id);
  });

  // Обновляем точки на логин странице
  document.querySelectorAll('.lltd').forEach(function(d){
    d.classList.toggle('active', d.getAttribute('data-lt')===id);
  });

  // Обновляем фон левой панели логина
  var loginPanel = document.getElementById('login-left-panel');
  if(loginPanel){
    THEMES.forEach(function(t){ loginPanel.classList.remove('login-theme-'+t.id); });
    loginPanel.classList.add('login-theme-'+id);
  }
}

function renderThemeGrid(containerId){
  var c=document.getElementById(containerId); if(!c) return;
  var lang=window._curLang||'ru';
  c.innerHTML='<div class="theme-grid">'
    +THEMES.map(function(t){
      var name=lang==='kk'?t.name_kk:t.name;
      return '<div class="theme-swatch'+(t.id===_currentTheme?' active':'')+'" data-theme="'+t.id+'" onclick="applyTheme(\''+t.id+'\')">'
        +'<div class="ts-dot" style="background:'+t.color+'"></div>'
        +t.emoji+' '+name
        +'<span class="ts-check">✓</span>'
        +'</div>';
    }).join('')
    +'</div>';
}

// Применяем тему при загрузке
document.addEventListener('DOMContentLoaded', function(){ applyTheme(_currentTheme); });

// ══════════════════════════════════════════════
//  ДОСТИЖЕНИЯ — ПОЛНЫЙ СПИСОК (20 штук)
// ══════════════════════════════════════════════
var ALL_ACHIEVEMENTS = [
  // Базовые
  { id:'first_call',   icon:'🌱', name:'Первый шаг',      name_kk:'Алғашқы қадам', desc:'Совершил первый звонок',  desc_kk:'Алғашқы қоңырауды жасадың',   xp:20,  cat:'basic',  cond:function(){return S.calls>=1;} },
  { id:'calls5',       icon:'💬', name:'Разговорчивый',   name_kk:'Сөйлегіш',      desc:'5 звонков',               desc_kk:'5 қоңырау',                    xp:30,  cat:'basic',  cond:function(){return S.calls>=5;} },
  { id:'calls10',      icon:'📞', name:'10 звонков',      name_kk:'10 қоңырау',    desc:'Настоящий болтун',        desc_kk:'Нағыз әңгімешіл',              xp:50,  cat:'basic',  cond:function(){return S.calls>=10;} },
  { id:'calls20',      icon:'👑', name:'Мастер',          name_kk:'Шебер',         desc:'20 звонков',              desc_kk:'20 қоңырау',                   xp:100, cat:'basic',  cond:function(){return S.calls>=20;} },
  { id:'calls50',      icon:'🌌', name:'Легенда',         name_kk:'Аңыз',          desc:'50 звонков',              desc_kk:'50 қоңырау',                   xp:200, cat:'basic',  cond:function(){return S.calls>=50;} },
  // Серии
  { id:'streak3',      icon:'🔥', name:'Три дня подряд',  name_kk:'Үш күн',        desc:'3 дня серии',             desc_kk:'3 күн қатарынан',              xp:25,  cat:'streak', cond:function(){return S.streak>=3;} },
  { id:'streak7',      icon:'🔥', name:'Неделя',          name_kk:'Апта',          desc:'7 дней серии',            desc_kk:'7 күн қатарынан',              xp:50,  cat:'streak', cond:function(){return S.streak>=7;} },
  { id:'streak30',     icon:'💎', name:'Месяц подряд',    name_kk:'Бір ай',        desc:'30 дней серии',           desc_kk:'30 күн қатарынан',             xp:150, cat:'streak', cond:function(){return S.streak>=30;} },
  // Время
  { id:'time30',       icon:'⏰', name:'Полчаса',         name_kk:'Жарты сағат',   desc:'30 минут общения',        desc_kk:'30 минут сөйлесу',             xp:30,  cat:'time',   cond:function(){return S.totalSecs>=1800;} },
  { id:'time60',       icon:'⭐', name:'Час общения',     name_kk:'Бір сағат',     desc:'1 час суммарно',          desc_kk:'Барлығы 1 сағат',              xp:60,  cat:'time',   cond:function(){return S.totalSecs>=3600;} },
  { id:'time300',      icon:'🏆', name:'5 часов',         name_kk:'5 сағат',       desc:'5 часов общения',         desc_kk:'5 сағат сөйлесу',              xp:120, cat:'time',   cond:function(){return S.totalSecs>=18000;} },
  // Контент
  { id:'creator',      icon:'✨', name:'Создатель',       name_kk:'Жасаушы',       desc:'Создал своего AI',        desc_kk:'Өз AI-ын жасады',              xp:50,  cat:'create', cond:function(){return S.customAgents&&S.customAgents.length>=1;} },
  { id:'creator3',     icon:'🎨', name:'Дизайнер ботов',  name_kk:'Боттар дизайнері',desc:'3 своих AI',            desc_kk:'3 өз AI-ы',                    xp:75,  cat:'create', cond:function(){return S.customAgents&&S.customAgents.length>=3;} },
  // Игры
  { id:'quiz_win',     icon:'🧠', name:'Знаток',          name_kk:'Білгіш',        desc:'Выиграй викторину',       desc_kk:'Викторинада жеңіс',            xp:30,  cat:'games',  cond:function(){return _gameStats.quizWins>=1;} },
  { id:'quiz5',        icon:'🎓', name:'Отличник',        name_kk:'Үздік',         desc:'5 побед в викторине',     desc_kk:'5 жеңіс',                      xp:60,  cat:'games',  cond:function(){return _gameStats.quizWins>=5;} },
  { id:'memory_win',   icon:'🃏', name:'Фотопамять',      name_kk:'Фотожад',       desc:'Выиграй в мемори',        desc_kk:'Жадта жеңіс',                  xp:30,  cat:'games',  cond:function(){return _gameStats.memoryWins>=1;} },
  { id:'word_win',     icon:'📝', name:'Словарник',       name_kk:'Сөздіктер',     desc:'Угадай слово',            desc_kk:'Сөзді тап',                    xp:30,  cat:'games',  cond:function(){return _gameStats.wordWins>=1;} },
  // Специальные
  { id:'night_owl',    icon:'🦉', name:'Ночная сова',     name_kk:'Түнгі үкі',     desc:'Звонок после 23:00',      desc_kk:'23:00-ден кейін қоңырау',      xp:25,  cat:'special',cond:function(){return _gameStats.nightCall;} },
  { id:'early_bird',   icon:'🐦', name:'Ранняя пташка',   name_kk:'Ерте тұрушы',   desc:'Звонок до 8:00',          desc_kk:'8:00-ден бұрын қоңырау',       xp:25,  cat:'special',cond:function(){return _gameStats.morningCall;} },
  { id:'polyglot',     icon:'🌍', name:'Полиглот',        name_kk:'Полиглот',      desc:'Звонки на 2 языках',      desc_kk:'2 тілде қоңырау',              xp:40,  cat:'special',cond:function(){return _gameStats.multiLang;} },
];

var _gameStats = (function(){
  try{ var s=localStorage.getItem('vivlos_game_stats'); return s?JSON.parse(s):{quizWins:0,memoryWins:0,wordWins:0,nightCall:false,morningCall:false,multiLang:false}; }
  catch(e){ return {quizWins:0,memoryWins:0,wordWins:0,nightCall:false,morningCall:false,multiLang:false}; }
})();

function saveGameStats(){ try{ localStorage.setItem('vivlos_game_stats',JSON.stringify(_gameStats)); }catch(e){} }

// Открытие модала достижений
function openAchModal(){
  var lang=window._curLang||'ru';
  var earned=ALL_ACHIEVEMENTS.filter(function(a){return a.cond();});
  var total=ALL_ACHIEVEMENTS.length;
  var cats={ basic:{ru:'Звонки',kk:'Қоңыраулар'}, streak:{ru:'Серии',kk:'Сериялар'},
             time:{ru:'Время',kk:'Уақыт'}, create:{ru:'Творчество',kk:'Шығармашылық'},
             games:{ru:'Игры',kk:'Ойындар'}, special:{ru:'Особые',kk:'Арнайы'} };

  var modal=document.createElement('div'); modal.className='ach-modal'; modal.id='_ach_modal';
  modal.innerHTML='<div class="ach-modal-card">'
    +'<div class="ach-modal-header">'
    +'<h2>🏆 '+(lang==='kk'?'Жетістіктер':'Достижения')+'</h2>'
    +'<button class="ach-modal-close" onclick="document.getElementById(\'_ach_modal\').remove()">✕</button>'
    +'</div>'
    +'<div class="ach-modal-body">'
    +'<div class="ach-modal-stats">'
    +'<div class="ach-stat-pill"><div class="asp-num">'+earned.length+'/'+total+'</div><div class="asp-lbl">'+(lang==='kk'?'Алынған':'Получено')+'</div></div>'
    +'<div class="ach-stat-pill"><div class="asp-num">'+earned.reduce(function(s,a){return s+a.xp;},0)+'</div><div class="asp-lbl">XP '+( lang==='kk'?'алынды':'получено')+'</div></div>'
    +'<div class="ach-stat-pill"><div class="asp-num">'+Math.round(earned.length/total*100)+'%</div><div class="asp-lbl">'+(lang==='kk'?'Аяқталды':'Завершено')+'</div></div>'
    +'</div>'
    +'<div class="ach-progress-bar"><div class="ach-progress-fill" style="width:'+(earned.length/total*100)+'%"></div></div>'
    +Object.keys(cats).map(function(cat){
      var catName=lang==='kk'?cats[cat].kk:cats[cat].ru;
      var items=ALL_ACHIEVEMENTS.filter(function(a){return a.cat===cat;});
      return '<div class="ach-cat-label">'+catName+'</div>'
        +'<div class="ach-full-grid">'
        +items.map(function(a){
          var unlocked=a.cond();
          var name=lang==='kk'?a.name_kk:a.name;
          var desc=lang==='kk'?a.desc_kk:a.desc;
          return '<div class="ach-full-item'+(unlocked?' earned':' locked')+'">'
            +(unlocked&&earned.indexOf(a)===earned.length-1?'<span class="afi-new">NEW</span>':'')
            +'<span class="afi-xp">+'+a.xp+' XP</span>'
            +'<span class="afi-icon">'+a.icon+'</span>'
            +'<div class="afi-name">'+name+'</div>'
            +'<div class="afi-desc">'+desc+'</div>'
            +'</div>';
        }).join('')
        +'</div>';
    }).join('')
    +'</div></div>';
  document.body.appendChild(modal);
  modal.addEventListener('click',function(e){if(e.target===modal)modal.remove();});
}

function updateAchievements(){
  // Обновляем минимальный грид на профиле
  var achList=document.querySelectorAll('.ach-item'); if(!achList.length) return;
  var conditions=[
    S.calls>=1, S.streak>=7, S.calls>=10, S.totalSecs>=3600,
    S.calls>=5&&S.totalSecs>=1500, S.calls>=3, S.history.length>=3, S.calls>=20,
    (S.customAgents&&S.customAgents.length>=1), S.streak>=30
  ];
  var earned=0;
  conditions.forEach(function(unlocked,i){
    if(!achList[i]) return;
    var wasLocked=achList[i].classList.contains('locked');
    if(unlocked){
      achList[i].classList.add('earned'); achList[i].classList.remove('locked'); earned++;
      if(wasLocked){
        var nm=achList[i].querySelector('.ach-name');
        if(nm) setTimeout(function(){_showAchToast(nm.textContent);},200);
        addXP('achievement');
      }
    } else {
      achList[i].classList.add('locked'); achList[i].classList.remove('earned');
    }
  });
  // Полный список
  ALL_ACHIEVEMENTS.forEach(function(a){
    if(a.cond()) addXP('achievement',0); // просто трекаем
  });
  S.achievements=ALL_ACHIEVEMENTS.filter(function(a){return a.cond();}).length;
  var el=document.getElementById('ds-ach'); if(el) el.textContent=S.achievements;
  // Ночной/утренний звонок
  var h=new Date().getHours();
  if(h>=23||h<1) _gameStats.nightCall=true;
  if(h>=6&&h<8) _gameStats.morningCall=true;
  saveGameStats();
}

// ══════════════════════════════════════════════
//  МИНИ-ИГРЫ
// ══════════════════════════════════════════════

// ── 1. ВИКТОРИНА ──────────────────────────────
var QUIZ_QUESTIONS_RU = [
  {q:'Сколько континентов на Земле?',opts:['5','6','7','8'],ans:2},
  {q:'Столица Казахстана?',opts:['Алматы','Астана','Шымкент','Атырау'],ans:1},
  {q:'Что такое AI?',opts:['Алгоритм инструкций','Искусственный интеллект','Авиационный институт','Анализ информации'],ans:1},
  {q:'Какой язык самый распространённый в мире?',opts:['Английский','Китайский','Испанский','Хинди'],ans:1},
  {q:'1+1=?',opts:['1','2','3','11'],ans:1},
  {q:'Сколько месяцев в году?',opts:['10','11','12','13'],ans:2},
  {q:'Скорость света?',opts:['300 км/с','3000 км/с','300 000 км/с','3 000 000 км/с'],ans:2},
  {q:'Автор "Войны и мира"?',opts:['Достоевский','Пушкин','Толстой','Чехов'],ans:2},
  {q:'Символ водорода в таблице Менделеева?',opts:['He','H','Ho','Hg'],ans:1},
  {q:'Кто написал "Абай жолы"?',opts:['Жамбыл','Мухтар Ауэзов','Сакен Сейфуллин','Абай Кунанбаев'],ans:1},
];
var QUIZ_QUESTIONS_KK = [
  {q:'Жерде қанша материк бар?',opts:['5','6','7','8'],ans:2},
  {q:'Қазақстанның астанасы?',opts:['Алматы','Астана','Шымкент','Атырау'],ans:1},
  {q:'AI дегеніміз не?',opts:['Алгоритм нұсқаулары','Жасанды интеллект','Авиация институты','Ақпарат талдау'],ans:1},
  {q:'Жылда қанша ай бар?',opts:['10','11','12','13'],ans:2},
  {q:'"Абай жолын" кім жазды?',opts:['Жамбыл','Мұхтар Әуезов','Сәкен Сейфуллин','Абай Құнанбаев'],ans:1},
  {q:'1+1=?',opts:['1','2','3','11'],ans:1},
  {q:'Жарық жылдамдығы?',opts:['300 км/с','3000 км/с','300 000 км/с','3 000 000 км/с'],ans:2},
  {q:'Ең үлкен мұхит?',opts:['Атлант','Үнді','Тынық мұхит','Арктика'],ans:2},
];

var _quizState={idx:0,score:0,done:false,total:7,questions:[]};

function openQuiz(){
  var lang=window._curLang||'ru';
  var pool=lang==='kk'?QUIZ_QUESTIONS_KK:QUIZ_QUESTIONS_RU;
  var shuffled=pool.slice().sort(function(){return Math.random()-.5;}).slice(0,7);
  _quizState={idx:0,score:0,done:false,total:shuffled.length,questions:shuffled};
  _renderQuiz();
}

function _renderQuiz(){
  var lang=window._curLang||'ru';
  var existing=document.getElementById('_game_modal'); if(existing) existing.remove();
  var modal=document.createElement('div'); modal.className='game-modal'; modal.id='_game_modal';
  if(_quizState.done){
    var pct=Math.round(_quizState.score/_quizState.total*100);
    var msg=pct>=80?(lang==='kk'?'Керемет! 🎉':'Отлично! 🎉'):pct>=50?(lang==='kk'?'Жаман емес!':'Неплохо!'):lang==='kk'?'Жаттық қажет':'Нужно потренироваться';
    modal.innerHTML='<div class="game-card"><button class="game-close" onclick="document.getElementById(\'_game_modal\').remove()">✕</button>'
      +'<h2>'+(lang==='kk'?'Нәтиже':'Результат')+'</h2>'
      +'<div class="quiz-score">'+_quizState.score+'/'+_quizState.total+'</div>'
      +'<div class="quiz-score-sub">'+msg+'</div>'
      +'<div style="margin-top:16px;text-align:center">'
      +'<button class="cbtn" style="display:inline-flex;padding:10px 24px" onclick="openQuiz()">'+(lang==='kk'?'Қайтадан':'Ещё раз')+'</button>'
      +'</div></div>';
    // XP + достижение
    var xpGain=10+_quizState.score*5;
    addXP('quiz',xpGain);
    if(pct>=70){_gameStats.quizWins++;saveGameStats();updateAchievements();}
  } else {
    var q=_quizState.questions[_quizState.idx];
    modal.innerHTML='<div class="game-card">'
      +'<button class="game-close" onclick="document.getElementById(\'_game_modal\').remove()">✕</button>'
      +'<h2>🧠 '+(lang==='kk'?'Викторина':'Викторина')+'</h2>'
      +'<div class="game-sub">'+(_quizState.idx+1)+' / '+_quizState.total+'</div>'
      +'<div class="quiz-q">'+q.q+'</div>'
      +'<div class="quiz-opts">'
      +q.opts.map(function(opt,i){
        return '<button class="quiz-opt" onclick="answerQuiz('+i+','+q.ans+')">'+(i===0?'A. ':i===1?'B. ':i===2?'C. ':'D. ')+opt+'</button>';
      }).join('')
      +'</div></div>';
  }
  document.body.appendChild(modal);
  modal.addEventListener('click',function(e){if(e.target===modal)modal.remove();});
}

function answerQuiz(chosen,correct){
  var btns=document.querySelectorAll('.quiz-opt');
  btns.forEach(function(b,i){b.disabled=true;if(i===correct)b.classList.add('correct');else if(i===chosen)b.classList.add('wrong');});
  if(chosen===correct) _quizState.score++;
  setTimeout(function(){
    _quizState.idx++;
    if(_quizState.idx>= _quizState.total) _quizState.done=true;
    _renderQuiz();
  },900);
}

// ── 2. МЕМОРИ ─────────────────────────────────
var MEMORY_EMOJIS=['🦊','🤖','🐉','🌸','⭐','🔮','🎨','🌿'];

var _memState={cards:[],flipped:[],matched:0,moves:0,lock:false};

function openMemory(){
  var deck=[]; MEMORY_EMOJIS.forEach(function(e){deck.push({emoji:e,id:Math.random()},{ emoji:e,id:Math.random()});});
  deck.sort(function(){return Math.random()-.5;});
  _memState={cards:deck,flipped:[],matched:0,moves:0,lock:false};
  _renderMemory();
}

function _renderMemory(){
  var lang=window._curLang||'ru';
  var existing=document.getElementById('_game_modal'); if(existing) existing.remove();
  var modal=document.createElement('div'); modal.className='game-modal'; modal.id='_game_modal';
  var allMatched=_memState.matched===MEMORY_EMOJIS.length;
  var html='<div class="game-card"><button class="game-close" onclick="document.getElementById(\'_game_modal\').remove()">✕</button>'
    +'<h2>🃏 '+(lang==='kk'?'Жады ойыны':'Мемори')+'</h2>'
    +'<div class="game-sub">'+(lang==='kk'?'Ходтар':'Ходы')+': '+_memState.moves
    +(allMatched?' 🎉 '+(lang==='kk'?'Жеңіс!':'Победа!'):'')+'</div>';
  if(allMatched){
    html+='<div class="quiz-score" style="font-size:48px">🎊</div>'
      +'<div class="quiz-score-sub">'+(lang==='kk'?_memState.moves+' ходта аяқталды':'Завершено за '+_memState.moves+' ходов')+'</div>'
      +'<div style="margin-top:14px;text-align:center"><button class="cbtn" style="display:inline-flex;padding:10px 24px" onclick="openMemory()">'+(lang==='kk'?'Қайтадан':'Ещё раз')+'</button></div>';
    addXP('memory',25);_gameStats.memoryWins++;saveGameStats();updateAchievements();
  } else {
    html+='<div class="memory-grid">'
      +_memState.cards.map(function(c,i){
        var isFlipped=_memState.flipped.indexOf(i)!==-1||_memState.matched>0&&_memState.cards.slice(0,i).filter(function(x){return x.emoji===c.emoji&&_memState.flipped.indexOf(_memState.cards.indexOf(x))!==-1;}).length>0;
        // Проверяем matched
        var isMatched=false;
        _memState.cards.forEach(function(cc,ii){
          if(cc.emoji===c.emoji&&_memState.flipped.indexOf(ii)!==-1&&_memState.matched>0) isMatched=true;
        });
        var show=_memState.flipped.indexOf(i)!==-1;
        var matched=c._matched||false;
        return '<div class="mem-card'+(show||matched?' flipped':'')+(matched?' matched':'')+'" onclick="flipCard('+i+')" data-idx="'+i+'">'+(show||matched?c.emoji:'')+'</div>';
      }).join('')+'</div>';
  }
  html+='</div>';
  modal.innerHTML=html;
  document.body.appendChild(modal);
  modal.addEventListener('click',function(e){if(e.target===modal)modal.remove();});
}

function flipCard(idx){
  if(_memState.lock||_memState.flipped.indexOf(idx)!==-1||_memState.cards[idx]._matched) return;
  _memState.flipped.push(idx);
  var cardEl=document.querySelector('[data-idx="'+idx+'"]');
  if(cardEl){cardEl.classList.add('flipped');cardEl.textContent=_memState.cards[idx].emoji;}
  if(_memState.flipped.length===2){
    _memState.lock=true; _memState.moves++;
    var i0=_memState.flipped[0],i1=_memState.flipped[1];
    if(_memState.cards[i0].emoji===_memState.cards[i1].emoji){
      _memState.cards[i0]._matched=true;_memState.cards[i1]._matched=true;
      _memState.matched++;_memState.flipped=[];_memState.lock=false;
      if(_memState.matched===MEMORY_EMOJIS.length){setTimeout(_renderMemory,400);}
    } else {
      setTimeout(function(){
        var c0=document.querySelector('[data-idx="'+i0+'"]'),c1=document.querySelector('[data-idx="'+i1+'"]');
        if(c0){c0.classList.remove('flipped');c0.textContent='';}
        if(c1){c1.classList.remove('flipped');c1.textContent='';}
        _memState.flipped=[];_memState.lock=false;
        // Update moves counter
        var sub=document.querySelector('.game-sub'); if(sub) sub.textContent=(window._curLang==='kk'?'Ходтар':'Ходы')+': '+_memState.moves;
      },800);
    }
  }
}

// ── 3. УГАДАЙ СЛОВО ───────────────────────────
var WORDS_RU=['ЛИСА','РОБОТ','ДРАКОН','ЗВОНОК','ПАМЯТЬ','УРОК','СИЛА','МИР','ОГОНЬ','СВЕТ'];
var WORDS_KK=['ТҮЛКІ','РОБОТ','АЙДАHАР','ОТТАЙ','ЖАРЫҚ','ОҚУ','КҮШ','ДҮНИЕ','ОТ','НҰР'];
var _wordState={word:'',guessed:[],wrong:0,maxWrong:6,done:false};

function openWordGame(){
  var lang=window._curLang||'ru'; var pool=lang==='kk'?WORDS_KK:WORDS_RU;
  var word=pool[Math.floor(Math.random()*pool.length)];
  _wordState={word:word,guessed:[],wrong:0,maxWrong:6,done:false,won:false};
  _renderWord();
}

function _renderWord(){
  var lang=window._curLang||'ru'; var w=_wordState;
  var existing=document.getElementById('_game_modal'); if(existing) existing.remove();
  var modal=document.createElement('div'); modal.className='game-modal'; modal.id='_game_modal';
  var display=w.word.split('').map(function(c){return w.guessed.indexOf(c)!==-1||w.done?c:'_';}).join(' ');
  var lives=Array(w.maxWrong).fill('❤️').map(function(_,i){return i<w.maxWrong-w.wrong?'❤️':'🖤';}).join('');
  var allGuessed=w.word.split('').every(function(c){return w.guessed.indexOf(c)!==-1;});
  var lost=w.wrong>=w.maxWrong;
  var html='<div class="game-card"><button class="game-close" onclick="document.getElementById(\'_game_modal\').remove()">✕</button>'
    +'<h2>📝 '+(lang==='kk'?'Сөзді тап':'Угадай слово')+'</h2>'
    +'<div class="word-display">'+display+'</div>'
    +'<div class="word-lives">'+lives+'</div>';
  if(allGuessed||lost){
    var msg=allGuessed?(lang==='kk'?'🎉 Тапты!':'🎉 Угадал!'):lang==='kk'?'💔 Жоғалды — '+w.word:'💔 Проиграл — '+w.word;
    html+='<div style="text-align:center;font-size:18px;font-weight:700;margin:12px 0;color:var(--blue)">'+msg+'</div>';
    html+='<div style="text-align:center"><button class="cbtn" style="display:inline-flex;padding:10px 24px" onclick="openWordGame()">'+(lang==='kk'?'Қайтадан':'Ещё раз')+'</button></div>';
    if(allGuessed){addXP('word',20);_gameStats.wordWins++;saveGameStats();updateAchievements();}
  } else {
    // Клавиатура
    var alphabet=lang==='kk'?'АӘБВГҒДЕЁЖЗИЙКҚЛМНҢОӨПРСТУҮҰФХҺЦЧШЩЪЫІЬЭЮЯ':'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ';
    html+='<div style="display:flex;flex-wrap:wrap;gap:5px;margin-top:12px;justify-content:center">'
      +alphabet.split('').map(function(l){
        var used=w.guessed.indexOf(l)!==-1;
        var isIn=w.word.indexOf(l)!==-1;
        var bg=used?(isIn?'background:#d1fae5;border-color:#10b981':'background:#fee2e2;border-color:#ef4444'):'';
        return '<button style="width:32px;height:32px;border-radius:8px;border:1.5px solid var(--border);background:var(--sky-pale);font-size:12px;font-weight:700;cursor:pointer;transition:all .15s;'+bg+'"'
          +(used?' disabled':'')+' onclick="guessLetter(\''+l+'\')">'+l+'</button>';
      }).join('')+'</div>';
  }
  html+='</div>';
  modal.innerHTML=html;
  document.body.appendChild(modal);
  modal.addEventListener('click',function(e){if(e.target===modal)modal.remove();});
}

function guessLetter(l){
  if(_wordState.guessed.indexOf(l)!==-1) return;
  _wordState.guessed.push(l);
  if(_wordState.word.indexOf(l)===-1) _wordState.wrong++;
  _renderWord();
}

// ══════════════════════════════════════════════
//  SETTINGS PAGE FIX — гарантированный вызов
// ══════════════════════════════════════════════
var _origDNavTo_v3 = window.dNavTo;
window.dNavTo = function(page){
  _origDNavTo_v3(page);
  if(page==='settings'){
    setTimeout(function(){
      initSettingsPage();
      renderThemeGrid('theme-grid-container');
    },50);
  }
};

// Следим за временем звонка (мультиязычность)
var _callLangs={}; 
var _origHandleSpeech=window.handleSpeech;
// Трекаем язык разговора
var _origInitSpeech=window.initSpeech;
window.initSpeech=function(chatId){
  var lang=window._curLang||'ru';
  _callLangs[lang]=true;
  if(Object.keys(_callLangs).length>=2){_gameStats.multiLang=true;saveGameStats();}
  if(_origInitSpeech) _origInitSpeech(chatId);
};

// Расширяем initSettingsPage темой
var _origInitSettingsPage = window.initSettingsPage;
window.initSettingsPage = function(){
  if(_origInitSettingsPage) _origInitSettingsPage();
  renderThemeGrid('theme-grid-container');
  // Синхронизируем тему
  document.querySelectorAll('.theme-swatch').forEach(function(sw){
    sw.classList.toggle('active',sw.dataset.theme===_currentTheme);
  });
};

// ── Vosk status check ──────────────────────────
async function checkVoskStatus(){
  try{
    var rRu=await fetch('/api/transcribe',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({audio_b64:'',lang:'ru'})});
    var dRu=await rRu.json(); var ruOk=!dRu.use_webspeech;
    var rKk=await fetch('/api/transcribe',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({audio_b64:'',lang:'kk'})});
    var dKk=await rKk.json(); var kkOk=!dKk.use_webspeech;
    var lang=window._curLang||'ru';
    document.querySelectorAll('[data-vosk-ru]').forEach(function(el){
      el.textContent=ruOk?'✅ Установлен':'⬇️ Не установлен';
      el.style.color=ruOk?'#10b981':'var(--muted)';
    });
    document.querySelectorAll('[data-vosk-kk]').forEach(function(el){
      el.textContent=kkOk?'✅ Установлен':(lang==='kk'?'🌐 Web Speech API':'🌐 Web Speech API');
      el.style.color=kkOk?'#10b981':'#f97316';
    });
  }catch(e){}
}

// Переопределяем initSettingsPage чтобы всегда работало
window.initSettingsPage=(function(orig){
  return function(){
    if(typeof orig==='function') orig();
    setTimeout(function(){
      renderThemeGrid('theme-grid-container');
      checkVoskStatus();
      var ls=document.getElementById('set-lang-ui'); if(ls) ls.value=window._curLang||'ru';
      var sl=document.getElementById('set-speech-lang'); if(sl) sl.value=(window.S&&window.S.speechLang)||'ru-RU';
      var nm=document.getElementById('set-name'); if(nm&&window.S&&window.S.user) nm.value=window.S.user.name||'';
      var av=document.getElementById('set-ava-preview');
      if(av&&window.S&&window.S.avatarUrl){ av.style.backgroundImage='url('+window.S.avatarUrl+')';av.style.backgroundSize='cover';av.textContent=''; }
      else if(av&&window.S&&window.S.user){ av.textContent=window.S.user.name?window.S.user.name[0].toUpperCase():'А'; }
      _setToggle('set-tog-tts',window.S?window.S.ttsOn:true);
      _setToggle('set-tog-speech',window.S?window.S.speechOn:true);
      _setToggle('set-tog-notif-bot',window.S?window.S.notifBotEnabled:true);
      _setToggle('set-tog-notif-streak',window.S?window.S.notifStreakEnabled:true);
      _setToggle('set-tog-notif-ach',window.S?window.S.notifAchEnabled:true);
      _renderBotAvatarSettings();
    },60);
  };
})(window.initSettingsPage);

// ── Обновлённый Vosk status через /api/vosk/status ──
window.checkVoskStatus = async function(){
  try{
    var r=await fetch('/api/vosk/status'); var d=await r.json();
    if(!d.ok) return;
    Object.keys(d.status).forEach(function(lang){
      var info=d.status[lang];
      document.querySelectorAll('[data-vosk-lang="'+lang+'"]').forEach(function(el){
        if(info.available){
          el.textContent='✅ Готов';
          el.style.color='#10b981';
        } else {
          el.textContent='❌ Не найден';
          el.style.color='#ef4444';
        }
      });
    });
  }catch(e){
    // Если сервер не отвечает — показываем Web Speech
    document.querySelectorAll('[data-vosk-lang]').forEach(function(el){
      el.textContent='🌐 Web Speech'; el.style.color='#f97316';
    });
  }
};

// ══ Login page theme switcher ════════════════════════════════
var _loginTheme = localStorage.getItem('vivlos_login_theme') || 'default';

// Только эти 2 темы синхронизируются с приложением
var LOGIN_SYNC_THEMES = ['default', 'dark'];

function setLoginTheme(theme, btn) {
  var panel = document.getElementById('login-left-panel');
  if(!panel) return;

  // Убираем все классы тем с левой панели
  var themes = ['default','galactic','forest','sunset','sakura','dark'];
  themes.forEach(function(t){ panel.classList.remove('login-theme-'+t); });

  // Применяем новую тему ТОЛЬКО на левую панель
  panel.classList.add('login-theme-' + theme);
  _loginTheme = theme;
  localStorage.setItem('vivlos_login_theme', theme);

  // Обновляем активную точку
  document.querySelectorAll('.lts-dot').forEach(function(d){
    d.classList.toggle('active', d.getAttribute('data-theme') === theme);
  });

  // Синхронизируем с основной темой ТОЛЬКО для синего и тёмного
  if(LOGIN_SYNC_THEMES.indexOf(theme) !== -1) {
    if(typeof applyTheme === 'function') applyTheme(theme);
  }
  // Остальные темы (галактика, лес, закат, сакура) — только левая панель,
  // форма входа всегда остаётся белой/синей
}

// Применяем сохранённую тему при загрузке логин страницы
document.addEventListener('DOMContentLoaded', function(){
  var saved = localStorage.getItem('vivlos_login_theme') || 'default';
  var panel = document.getElementById('login-left-panel');
  if(panel) {
    panel.classList.add('login-theme-' + saved);
    document.querySelectorAll('.lts-dot').forEach(function(d){
      d.classList.toggle('active', d.getAttribute('data-theme') === saved);
    });
  }
  // Синхронизируем глобальную тему только для синего/тёмного
  if(LOGIN_SYNC_THEMES.indexOf(saved) !== -1 && typeof applyTheme === 'function') {
    applyTheme(saved);
  }
});

// ══════════════════════════════════════════════
//  НОВЫЙ ДИЗАЙН ЗВОНКА — функции
// ══════════════════════════════════════════════

// Переключение вкладок чат/игры
function switchCallTab(tab, btn) {
  var chatEl  = document.getElementById('dc-chat');
  var gamesEl = document.getElementById('call-games-panel');
  var tabs    = document.querySelectorAll('.call-tab-btn');

  tabs.forEach(function(b){ b.classList.remove('active'); });
  if(btn) btn.classList.add('active');
  else {
    tabs.forEach(function(b){
      if((tab==='chat'&&b.textContent.includes('💬'))||(tab==='games'&&b.textContent.includes('🎮')))
        b.classList.add('active');
    });
  }

  if(chatEl)  chatEl.style.display  = tab==='chat'  ? 'flex' : 'none';
  if(gamesEl) gamesEl.classList.toggle('active', tab==='games');
}

// Загрузка фото/видео для AI
function triggerMediaUpload() {
  var inp = document.getElementById('call-media-input');
  if(inp) inp.click();
}

var _callMediaData = null;
var _callMediaType = null;

function handleCallMedia(input) {
  var file = input.files[0]; if(!file) return;
  var isVideo = file.type.startsWith('video/');
  var isImage = file.type.startsWith('image/');
  if(!isVideo && !isImage) { alert('Только фото или видео'); return; }
  if(file.size > 50*1024*1024) { alert('Максимум 50 МБ'); return; }

  var reader = new FileReader();
  reader.onload = function(e) {
    _callMediaData = e.target.result;
    _callMediaType = isVideo ? 'video' : 'image';

    // Показываем превью
    var prev = document.getElementById('call-media-preview');
    if(prev) {
      prev.style.display = '';
      prev.innerHTML = '<button class="remove-media" onclick="removeCallMedia()">✕</button>'
        + (isImage
          ? '<img src="'+e.target.result+'" alt="preview">'
          : '<video src="'+e.target.result+'" controls muted style="width:100%;max-height:140px"></video>'
        );
    }

    // Для изображений — отправляем через Vision API
    if(isImage) {
      var lang = window._curLang || window._callLang || 'ru';
      var userPrompt = lang==='kk'
        ? 'Мен саған сурет жібердім. Не көресің?'
        : lang==='de'
        ? 'Ich habe dir ein Bild geschickt. Was siehst du?'
        : lang==='en'
        ? 'I sent you a photo. What do you see?'
        : 'Я отправил тебе фото. Что видишь? Расскажи.';

      // Показываем сообщение пользователя с превью
      var chatId = isDesktop ? 'dc-chat' : 'c-chat';
      var ch = document.getElementById(chatId);
      if(ch) {
        var div = document.createElement('div');
        div.className = 'bubble user';
        div.innerHTML = '<img src="'+e.target.result+'" style="max-width:200px;border-radius:12px;display:block;margin-bottom:6px">'
          + '<div>'+_esc(userPrompt)+'</div>'
          + '<div class="bubble-time">'+_nowTime()+'</div>';
        ch.appendChild(div);
        ch.scrollTop = ch.scrollHeight;
      }
      chatHistory.push({role:'user', content: userPrompt});

      // Вызываем Vision API
      sendImageToAI(e.target.result, userPrompt);
    } else {
      // Видео — только текстовый промпт
      var lang = window._curLang || 'ru';
      var prompt = lang==='kk' ? 'Мен саған видео жібердім.' : 'Я отправил тебе видео.';
      handleSpeech(prompt);
    }
  };
  reader.readAsDataURL(file);
}

// Vision — отправляет картинку в AI и получает ответ
async function sendImageToAI(imageBase64, userText) {
  if(aiThinking) return;
  aiThinking = true;
  window._lastUserSpokeTs = Date.now();

  var _hang = setTimeout(function() {
    aiThinking = false; window._speechInProgress = false;
  }, 30000);

  var chatId = isDesktop ? 'dc-chat' : 'c-chat';
  var thinkEl = _addThinkingBubble(chatId);
  setStatus('● Смотрит на фото...');

  try {
    var r = await fetch('/api/chat/vision', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        image:      imageBase64,
        message:    userText,
        agent:      (window.agent && window.agent.id) || 'ari',
        lang:       window._callLang || window._curLang || 'ru',
        user_name:  S.user.name || '',
        user_age:   S.user.age || 'adult',
        messages:   chatHistory.slice(-6),
        emotion:    window.lastEmotion || 'neutral',
      })
    });
    var data = await r.json();
    var reply = (data.ok && data.reply) ? data.reply : fallback();
    thinkEl.remove();
    _addBubbleRich('ai', reply, chatId);
    chatHistory.push({role:'assistant', content: reply});
    window._lastAiRespondedTs = Date.now();
    setStatus('● Говорит...'); orbSpeak(true); speak(reply);
  } catch(e) {
    thinkEl.remove();
    var fb = fallback();
    _addBubbleRich('ai', fb, chatId);
    chatHistory.push({role:'assistant', content: fb});
    setStatus('● Онлайн'); orbSpeak(false); aiThinking = false;
  } finally {
    clearTimeout(_hang);
  }
}

function removeCallMedia() {
  _callMediaData = null; _callMediaType = null;
  var prev = document.getElementById('call-media-preview');
  if(prev) prev.style.display = 'none';
  var inp = document.getElementById('call-media-input');
  if(inp) inp.value = '';
}

// AI рассказывает интересный факт
function askAIFact() {
  var lang = window._curLang || 'ru';
  var prompts = {
    ru: ['Расскажи мне один удивительный факт о Казахстане!',
         'Поделись интересным фактом из науки!',
         'Расскажи что-нибудь необычное о космосе!',
         'Удиви меня интересным историческим фактом!'],
    kk: ['Қазақстан туралы таңғаладыратын бір факт айтшы!',
         'Ғылым туралы қызықты факт бөліс!',
         'Ғарыш туралы таңқаларлық нәрсе айт!',
         'Тарихтан қызықты бір факт таңқалдырт!'],
  };
  var pool = prompts[lang] || prompts.ru;
  var prompt = pool[Math.floor(Math.random()*pool.length)];
  handleSpeech(prompt);
  addXP('quiz', 5);
  switchCallTab('chat');
}

// Обновляем orbSpeak для нового дизайна
var _origOrbSpeak = window.orbSpeak;
window.orbSpeak = function(on) {
  // Call original with classList fix
  if(_origOrbSpeak) _origOrbSpeak(on);
  // Status — use classList.toggle not className=
  var status = document.getElementById('dc-status');
  if(status) {
    status.textContent = on ? '● Говорит...' : '● Онлайн';
    status.classList.toggle('speaking', !!on);
  }
  var wviz = document.getElementById('dwviz');
  if(wviz) wviz.classList.toggle('paused', !on);
};

// Удалить аватар пользователя
function deleteAvatar() {
  if(!confirm('Удалить фото профиля?')) return;
  S.avatarUrl = null;
  localStorage.removeItem('vivlos_avatar');
  _applyAvatarAll();
  var prev = document.getElementById('set-ava-preview');
  if(prev) { prev.style.backgroundImage=''; prev.textContent = S.user.name?S.user.name[0].toUpperCase():'А'; }
  var delBtn = document.getElementById('del-ava-btn');
  if(delBtn) delBtn.style.display = 'none';
  showToast('Фото удалено');
}

// Показывать кнопку удаления если есть аватар
var _origUploadAvatar = window.uploadAvatar;
window.uploadAvatar = function(input) {
  if(_origUploadAvatar) _origUploadAvatar(input);
  setTimeout(function(){
    var delBtn = document.getElementById('del-ava-btn');
    if(delBtn && S.avatarUrl) delBtn.style.display = '';
  }, 500);
};

// При открытии настроек показываем кнопку удаления если есть аватар
var _prevInitSettings = window.initSettingsPage;
window.initSettingsPage = function() {
  if(_prevInitSettings) _prevInitSettings();
  setTimeout(function(){
    var delBtn = document.getElementById('del-ava-btn');
    if(delBtn) delBtn.style.display = S.avatarUrl ? '' : 'none';
  }, 100);
};

// setLoginTheme — используем новые точки .lltd
window.setLoginTheme = function(theme, el) {
  var panel = document.getElementById('login-left-panel');
  if(!panel) return;
  var themes = ['default','galactic','forest','sunset','sakura','dark'];
  themes.forEach(function(t){ panel.classList.remove('login-theme-'+t); });
  panel.classList.add('login-theme-' + theme);
  localStorage.setItem('vivlos_login_theme', theme);

  document.querySelectorAll('.lltd').forEach(function(d){
    d.classList.toggle('active', d.getAttribute('data-lt') === theme);
  });

  // Синхронизируем только синий и тёмный с приложением
  if(theme === 'default' || theme === 'dark') {
    if(typeof applyTheme === 'function') applyTheme(theme);
  }
};

// Инициализация точек темы на логине при загрузке
document.addEventListener('DOMContentLoaded', function(){
  var saved = localStorage.getItem('vivlos_login_theme') || 'default';
  var panel = document.getElementById('login-left-panel');
  if(panel) {
    panel.classList.add('login-theme-' + saved);
    document.querySelectorAll('.lltd').forEach(function(d){
      d.classList.toggle('active', d.getAttribute('data-lt') === saved);
    });
  }
  if((saved==='default'||saved==='dark') && typeof applyTheme==='function') applyTheme(saved);
});
// ══ Статус движка AI (Gemini / Ollama / Offline) ══════════
var _lastEngine = null;

// Engine status display (no handleSpeech override here — done in streaming section)

// Показываем статус движка в интерфейсе
function _showEngineStatus(engine) {
  if(engine === _lastEngine) return;
  _lastEngine = engine;
  var labels = {
    'gpt-4o-mini': '🤖 GPT-4o',
    'gemini':      '🌐 Gemini',
    'openrouter':  '🔀 OpenRouter',
    'groq':        '⚡ Groq',
    'ollama':      '💻 Ollama',
    'offline':     '📵 Offline',
  };
  var colors = {
    'gpt-4o-mini': '#10b981',
    'gemini':      '#0ea5e9',
    'openrouter':  '#6366f1',
    'groq':        '#f59e0b',
    'ollama':      '#f97316',
    'offline':     '#ef4444',
  };
  var label = labels[engine] || engine;
  var color = colors[engine] || '#94a3b8';

  // Обновляем статус в call overlay
  var statusEl = document.getElementById('dc-status');
  if(statusEl) {
    var engineBadge = document.getElementById('_engine_badge');
    if(!engineBadge) {
      engineBadge = document.createElement('span');
      engineBadge.id = '_engine_badge';
      engineBadge.style.cssText = 'font-size:10px;margin-left:8px;padding:2px 8px;border-radius:99px;font-weight:700;';
      statusEl.appendChild(engineBadge);
    }
    engineBadge.textContent = label;
    engineBadge.style.background = color + '22';
    engineBadge.style.color = color;
  }

  // Если офлайн — показываем тост
  if(engine === 'ollama') {
    showToast('💻 Ollama — работаем офлайн!');
  } else if(engine === 'offline') {
    showToast('📵 Нет сети — базовый режим', true);
  }
}

// Патчим fetch для /api/chat чтобы видеть движок
var _origFetch = window.fetch;
window.fetch = function(url, opts) {
  var p = _origFetch.apply(this, arguments);
  if(url && url.toString().includes('/api/chat')) {
    return p.then(function(resp) {
      resp.clone().json().then(function(d) {
        if(d && d.engine) _showEngineStatus(d.engine);
      }).catch(function(){});
      return resp;
    });
  }
  return p;
};

// Проверяем Ollama при старте
async function _checkOllamaOnStart() {
  try {
    var r = await _origFetch('/api/ollama/status');
    var d = await r.json();
    if(d.available) {
      console.log('✅ Ollama доступен:', d.model, 'на', d.url);
    } else {
      console.log('ℹ️ Ollama не запущен — только Gemini онлайн');
    }
  } catch(e) {}
}
document.addEventListener('DOMContentLoaded', function() {
  setTimeout(_checkOllamaOnStart, 2000);
});
// ══════════════════════════════════════════════
//  STREAMING AI responses (токен за токеном)
//  Как ChatGPT — текст появляется постепенно
// ══════════════════════════════════════════════

var _streamController = null;  // для отмены

// Показываем typing bubble (три точки)
function showTypingBubble() {
  var chat = document.getElementById('dc-chat');
  if(!chat) return;
  var existing = document.getElementById('_typing_bubble');
  if(existing) return;
  var bubble = document.createElement('div');
  bubble.id = '_typing_bubble';
  bubble.className = 'bubble ai';
  bubble.style.cssText = 'padding:12px 16px;display:flex;align-items:center;gap:4px;';
  bubble.innerHTML = '<span style="width:7px;height:7px;border-radius:50%;background:var(--muted);animation:typingDot 1.2s ease-in-out infinite"></span>'
    + '<span style="width:7px;height:7px;border-radius:50%;background:var(--muted);animation:typingDot 1.2s ease-in-out .25s infinite"></span>'
    + '<span style="width:7px;height:7px;border-radius:50%;background:var(--muted);animation:typingDot 1.2s ease-in-out .5s infinite"></span>';
  chat.appendChild(bubble);
  chat.scrollTop = chat.scrollHeight;
}

function removeTypingBubble() {
  var b = document.getElementById('_typing_bubble');
  if(b) b.remove();
}

// Стримим ответ (SSE / fetch streaming)
async function streamAIReply(message, agentId, lang) {
  // Показываем typing indicator
  showTypingBubble();

  // Создаём пустой bubble для постепенного заполнения
  var chat = document.getElementById('dc-chat');
  var streamBubble = null;
  var fullText = '';

  try {
    var response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message:   message,
        agent_id:  agentId,
        lang:      lang,
        user_id:   window.S && window.S.user ? window.S.user.id : null,
      })
    });

    if(!response.ok) throw new Error('stream failed');
    if(!response.body)  throw new Error('no body');

    removeTypingBubble();

    // Создаём bubble для стриминга
    if(chat) {
      streamBubble = document.createElement('div');
      streamBubble.className = 'bubble ai';
      streamBubble.innerHTML = '<span class="bubble-text"></span>'
        + '<span class="bubble-time">'+new Date().toLocaleTimeString('ru',{hour:'2-digit',minute:'2-digit'})+'</span>';
      chat.appendChild(streamBubble);
    }

    // Читаем SSE поток
    var reader = response.body.getReader();
    var decoder = new TextDecoder();
    var buffer = '';

    while(true) {
      var result = await reader.read();
      if(result.done) break;

      buffer += decoder.decode(result.value, { stream: true });
      var lines = buffer.split('\n');
      buffer = lines.pop();

      for(var line of lines) {
        if(!line.startsWith('data: ')) continue;
        var payload = line.slice(6).trim();
        if(payload === '[DONE]') {
          // Стриминг завершён
          if(fullText) {
            // Воспроизводим через TTS
            if(window.S && window.S.ttsOn) speakText(fullText, lang);
          }
          return fullText;
        }
        try {
          var d = JSON.parse(payload);
          if(d.token && streamBubble) {
            fullText += d.token;
            var textEl = streamBubble.querySelector('.bubble-text');
            if(textEl) textEl.textContent = fullText;
            if(chat) chat.scrollTop = chat.scrollHeight;
          }
        } catch(e) {}
      }
    }
  } catch(err) {
    removeTypingBubble();
    console.warn('Streaming error, fallback to regular chat:', err);
    return null;  // вернём null → фронт использует обычный /api/chat
  }
  return fullText;
}

// Перехватываем sendMessage чтобы попробовать streaming сначала
// Streaming handleSpeech override removed - using original handleSpeech directly

// Анимация для typing dots (CSS в JS чтобы не менять файл)
(function() {
  if(document.getElementById('_typing_style')) return;
  var style = document.createElement('style');
  style.id = '_typing_style';
  style.textContent = `
    @keyframes typingDot {
      0%,80%,100% { transform: scale(1); opacity:.4; }
      40%          { transform: scale(1.4); opacity:1; }
    }
    .bubble-text { white-space: pre-wrap; word-break: break-word; }
    .bubble-time { display:block; font-size:10px; opacity:.5; margin-top:4px; }
  `;
  document.head.appendChild(style);
})();
// ══ Язык разговора в видеозвонке ════════════════════════════

var _callLang     = window._curLang || 'ru';  // текущий язык звонка
var _callLangMap  = { ru:'ru-RU', kk:'kk-KZ', en:'en-US', de:'de-DE' };
var _callLangName = { ru:'Русский', kk:'Қазақша', en:'English', de:'Deutsch' };

function setCallLang(lang, flag, bcp47) {
  _callLang = lang;
  window._callLang = lang;

  // Обновляем флаг и код на кнопке
  var flagEl = document.getElementById('call-lang-flag');
  if(flagEl) flagEl.textContent = flag;
  var codeEl = document.getElementById('call-lang-code');
  if(codeEl) codeEl.textContent = lang.toUpperCase();

  // Подсвечиваем активный
  document.querySelectorAll('.call-lang-opt').forEach(function(b) {
    b.classList.toggle('active', b.getAttribute('data-cl') === lang);
  });

  // Закрываем меню
  var menu = document.getElementById('call-lang-menu');
  if(menu) menu.style.display = 'none';

  // Обновляем язык распознавания речи
  if(window.recognition) {
    window.recognition.lang = bcp47;
    if(window.isListening) {
      try { window.recognition.stop(); } catch(e) {}
      setTimeout(function() {
        if(window.micOn) startListening();
      }, 500);
    }
  }

  // Показываем тост
  var names = { ru:'🇷🇺 Русский', kk:'🇰🇿 Қазақша', en:'🇬🇧 English', de:'🇩🇪 Deutsch' };
  showToast && showToast(names[lang] || lang);

  console.log('🌐 Call language:', lang, bcp47);
}

function toggleCallLangMenu() {
  var menu = document.getElementById('call-lang-menu');
  if(!menu) return;
  var isOpen = menu.style.display !== 'none';
  menu.style.display = isOpen ? 'none' : 'flex';

  // Подсвечиваем текущий язык
  document.querySelectorAll('.call-lang-opt').forEach(function(b) {
    b.classList.toggle('active', b.getAttribute('data-cl') === _callLang);
  });
}

// Закрывать меню при клике вне
document.addEventListener('click', function(e) {
  var wrap = document.getElementById('call-lang-wrap');
  if(wrap && !wrap.contains(e.target)) {
    var menu = document.getElementById('call-lang-menu');
    if(menu) menu.style.display = 'none';
  }
});

// Sync callLang with handleSpeech — use _callLang if set
var _origHandleSpeechLang = window.handleSpeech;
window.handleSpeech = async function(text) {
  // Use call language for AI response
  if(window._callLang) window._curLang = window._callLang;
  if(typeof _origHandleSpeechLang === 'function') {
    return _origHandleSpeechLang(text);
  }
};

// Init flag on call start
(function() {
  var saved = window._curLang || 'ru';
  var flags = { ru:'🇷🇺', kk:'🇰🇿', en:'🇬🇧', de:'🇩🇪' };
  setTimeout(function() {
    var btn = document.getElementById('call-lang-flag');
    if(btn) btn.textContent = flags[saved] || '🇷🇺';
    document.querySelectorAll('.call-lang-opt').forEach(function(b) {
      b.classList.toggle('active', b.getAttribute('data-cl') === saved);
    });
    _callLang = saved;
    window._callLang = saved;
  }, 1000);
})();
// ══ Whisper STT — используется если доступен (лучше Web Speech) ══
var _whisperAvail = false;
var _mediaRecorder = null;
var _audioChunks = [];
var _isRecordingForWhisper = false;

// Проверяем доступность Whisper на старте
fetch('/api/stt/status').then(r=>r.json()).then(function(d){
  _whisperAvail = d.whisper || false;
  if(_whisperAvail) console.log('✅ Whisper STT available — using as primary');
  else console.log('ℹ️ Whisper not available — using Web Speech');
}).catch(function(){});

async function transcribeWithWhisper(audioBlob, lang) {
  try {
    var reader = new FileReader();
    return new Promise(function(resolve) {
      reader.onload = async function() {
        var b64 = reader.result.split(',')[1];
        var r = await fetch('/api/transcribe', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({audio_b64: b64, lang: lang || window._callLang || window._curLang || 'ru'})
        });
        var d = await r.json();
        if(d.ok && d.text) resolve(d.text);
        else resolve(null);
      };
      reader.readAsDataURL(audioBlob);
    });
  } catch(e) { return null; }
}

// ══════════════════════════════════════════════════════════════
//  REALTIME AUDIO LOOP
//  Архитектура:
//  AudioWorklet(VAD) → base64 chunks → SocketIO →
//  Server(Whisper+AI stream) → rt_ai_token → display + TTS
// ══════════════════════════════════════════════════════════════

var _rtActive       = false;   // realtime loop running
var _rtAudioCtx     = null;    // AudioContext
var _rtWorklet      = null;    // AudioWorkletNode
var _rtSource       = null;    // MediaStreamSource
var _rtAiSpeaking   = false;   // AI currently streaming
var _rtSpeaking     = false;   // user currently speaking (VAD)
var _rtReplyBuffer  = '';      // accumulated AI tokens
var _rtThinkEl      = null;    // "thinking" bubble

// ── Init realtime loop ───────────────────────────────────────
async function startRealtimeLoop(stream, lang, agentId) {
  if(_rtActive) return;
  if(!window.socket) {
    console.warn('RT: no socket.io connection');
    return;
  }

  lang    = lang    || window._callLang || window._curLang || 'ru';
  agentId = agentId || (window.agent && window.agent.id) || 'ari';

  // Init server session
  window.socket.emit('rt_init', { lang: lang, agent_id: agentId });

  try {
    _rtAudioCtx = new AudioContext({ sampleRate: 48000 });
    await _rtAudioCtx.audioWorklet.addModule('/static/vad-processor.js');
    _rtSource  = _rtAudioCtx.createMediaStreamSource(stream);
    _rtWorklet = new AudioWorkletNode(_rtAudioCtx, 'vad-processor');

    _rtWorklet.port.onmessage = function(e) {
      if(e.data.type !== 'chunk') return;
      _onRtChunk(e.data);
    };

    _rtSource.connect(_rtWorklet);
    _rtWorklet.connect(_rtAudioCtx.destination);
    _rtActive = true;

    _setupRtSocketEvents(lang, agentId);
    console.log('✅ Realtime Audio Loop started:', lang, agentId);

  } catch(err) {
    console.warn('RT init error:', err);
    _rtActive = false;
  }
}

function stopRealtimeLoop() {
  _rtActive = false;
  try {
    if(_rtWorklet)  { _rtWorklet.disconnect(); _rtWorklet = null; }
    if(_rtSource)   { _rtSource.disconnect();  _rtSource  = null; }
    if(_rtAudioCtx) { _rtAudioCtx.close();     _rtAudioCtx = null; }
  } catch(e) {}
  window.socket && window.socket.emit('rt_interrupt', {});
  console.log('RT: loop stopped');
}

// ── Send audio chunk to server ───────────────────────────────
var _rtChunkBatch = []; // accumulate a few chunks before sending
var _rtChunkTimer = null;

function _onRtChunk(data) {
  if(!_rtActive || aiThinking) return;

  var isSpeech = data.is_speech;

  // Interrupt AI if user speaks
  if(isSpeech && _rtAiSpeaking) {
    _interruptAI();
    return;
  }

  // Encode PCM to base64
  var pcm    = new Int16Array(data.pcm);
  var bytes  = new Uint8Array(pcm.buffer);
  var b64    = btoa(String.fromCharCode.apply(null, bytes));

  _rtChunkBatch.push({ b64: b64, is_speech: isSpeech });

  // Debounce: send every 100ms
  clearTimeout(_rtChunkTimer);
  _rtChunkTimer = setTimeout(function() {
    if(_rtChunkBatch.length === 0) return;
    // Merge batched chunks
    var allPcm = '';
    var anySpeech = false;
    for(var c of _rtChunkBatch) {
      allPcm += c.b64;
      if(c.is_speech) anySpeech = true;
    }
    _rtChunkBatch = [];

    window.socket.emit('rt_audio_chunk', {
      pcm_b64:     allPcm,
      is_speech:   anySpeech,
      sample_rate: 16000,
    });
  }, 100);
}

// ── Interrupt AI ─────────────────────────────────────────────
function _interruptAI() {
  _rtAiSpeaking = false;
  _rtReplyBuffer = '';
  window.socket.emit('rt_interrupt', { reason: 'user_spoke' });
  // Remove partial AI bubble
  var ch = document.getElementById(isDesktop ? 'dc-chat' : 'c-chat');
  if(ch) {
    var streaming = ch.querySelector('.bubble.ai.streaming');
    if(streaming) streaming.remove();
  }
  // Stop TTS
  window.speechSynthesis && window.speechSynthesis.cancel();
  if(window._ttsAudio) { window._ttsAudio.pause(); window._ttsAudio = null; }
  console.log('RT: AI interrupted by user');
}

// ── Socket.IO event handlers ─────────────────────────────────
function _setupRtSocketEvents(lang, agentId) {
  if(!window.socket) return;

  // Server confirmed transcription
  window.socket.on('rt_transcript', function(data) {
    if(!data.text) return;
    var ch = document.getElementById(isDesktop ? 'dc-chat' : 'c-chat');
    _addBubbleRich('user', data.text, isDesktop ? 'dc-chat' : 'c-chat');
    chatHistory.push({ role: 'user', content: data.text });
  });

  // AI token streaming
  window.socket.on('rt_ai_token', function(data) {
    _rtAiSpeaking = true;
    _rtReplyBuffer += (data.token || '');

    var ch = document.getElementById(isDesktop ? 'dc-chat' : 'c-chat');
    if(!ch) return;

    // Find or create streaming bubble
    var bubble = ch.querySelector('.bubble.ai.streaming');
    if(!bubble) {
      if(_rtThinkEl) { _rtThinkEl.remove(); _rtThinkEl = null; }
      bubble = document.createElement('div');
      bubble.className = 'bubble ai streaming';
      bubble.innerHTML = '<div class="stream-text"></div><div class="bubble-time">'+_nowTime()+'</div>';
      ch.appendChild(bubble);
    }
    bubble.querySelector('.stream-text').textContent = _rtReplyBuffer;
    ch.scrollTop = ch.scrollHeight;
  });

  // AI done streaming
  window.socket.on('rt_ai_done', function(data) {
    _rtAiSpeaking = false;
    var ch = document.getElementById(isDesktop ? 'dc-chat' : 'c-chat');
    if(ch) {
      var bubble = ch.querySelector('.bubble.ai.streaming');
      if(bubble) bubble.classList.remove('streaming');
    }
    var fullText = data.text || _rtReplyBuffer;
    _rtReplyBuffer = '';

    if(fullText && !data.interrupted) {
      chatHistory.push({ role: 'assistant', content: fullText });
      window._lastAiRespondedTs = Date.now();
      // TTS
      if(S.ttsOn) speak(fullText);
    }
  });

  // Status updates
  window.socket.on('rt_processing', function(data) {
    var status = data.status;
    if(status === 'transcribing') setStatus('● Распознаю...');
    else if(status === 'thinking') {
      setStatus('● Думает...');
      orbSpeak(false);
      var chatId = isDesktop ? 'dc-chat' : 'c-chat';
      _rtThinkEl = _addThinkingBubble(chatId);
    }
    else if(status === 'idle') {
      setStatus('● Слушаю...');
      orbSpeak(false);
    }
  });

  window.socket.on('rt_listening', function(data) {
    if(data.active) { setStatus('● Слышу...'); setWave(true); }
    else setWave(false);
  });

  window.socket.on('rt_ready', function(data) {
    console.log('RT: server ready', data);
    setStatus('● Слушаю (RT)...');
  });
}

// ── Auto-start RT loop when call begins ─────────────────────
var _origStartCall = window.startCall;
window.startCall = function(agentData) {
  if(_origStartCall) _origStartCall(agentData);
  // Wait for camera/mic stream to be ready
  setTimeout(function() {
    if(window.combinedStream && window.combinedStream.active) {
      var lang    = window._callLang || window._curLang || 'ru';
      var agentId = window.agent && window.agent.id || 'ari';
      startRealtimeLoop(window.combinedStream, lang, agentId);
    }
  }, 2000);
};

// Stop RT loop on call end
var _origEndCall = window.endCall;
window.endCall = function() {
  stopRealtimeLoop();
  if(_origEndCall) _origEndCall();
};

// Update RT lang when language switcher changes
var _origSetCallLang = window.setCallLang;
window.setCallLang = function(lang, flag, bcp47) {
  if(_origSetCallLang) _origSetCallLang(lang, flag, bcp47);
  if(_rtActive && window.socket) {
    window.socket.emit('rt_lang', { lang: lang });
  }
};


// ══════════════════════════════════════════════════════════════
//  VIVLOS — ALWAYS-VISIBLE EMOTION STRIP (mobile + desktop call)
//  Displays the current emotion supplied by the face-analysis layer.
// ══════════════════════════════════════════════════════════════
(function installEmotionStrip(){
  if (window.__vivlosEmotionStripInstalled) return;
  window.__vivlosEmotionStripInstalled = true;

  var emotionItems = [
    ['happy','😊','Радость'], ['sad','😢','Грусть'],
    ['angry','😠','Злость'], ['surprised','😮','Удивление'],
    ['fearful','😨','Страх'], ['neutral','😐','Нейтрально'],
    ['focused','🧐','Фокус']
  ];
  var stripTimer = null;

  function currentEmotion(){
    var e = window.lastEmotion || lastEmotion || 'neutral';
    if (window.faceData && typeof window.faceData === 'object') {
      e = window.faceData.emotion || window.faceData.expression || e;
    }
    e = String(e || 'neutral').toLowerCase();
    // Normalize common labels emitted by face-analysis libraries.
    if (e === 'surprise') e = 'surprised';
    if (e === 'fear') e = 'fearful';
    if (e === 'sadness') e = 'sad';
    if (e === 'happiness') e = 'happy';
    if (e === 'anger') e = 'angry';
    return emotionItems.some(function(x){ return x[0] === e; }) ? e : 'neutral';
  }

  function ensureStrip(){
    var strip = document.getElementById('vivlos-emotion-strip');
    if (!strip) {
      strip = document.createElement('div');
      strip.id = 'vivlos-emotion-strip';
      strip.setAttribute('aria-label','Эмоции во время видеозвонка');
      strip.innerHTML =
        '<div class="ves-head"><span class="ves-live-dot"></span><span>ЭМОЦИИ</span>' +
        '<span class="ves-current-label" id="ves-current-label">Нейтрально</span></div>' +
        '<div class="ves-items" id="ves-items"></div>';
      document.body.appendChild(strip);
      var items = document.getElementById('ves-items');
      emotionItems.forEach(function(item){
        var el = document.createElement('div');
        el.className = 'ves-item';
        el.setAttribute('data-emotion', item[0]);
        el.innerHTML = '<span class="ves-emoji">'+item[1]+'</span><span class="ves-name">'+item[2]+'</span>';
        items.appendChild(el);
      });
    }
    return strip;
  }

  function render(){
    var callVisible = !!(
      (document.getElementById('s-call') && document.getElementById('s-call').classList.contains('active')) ||
      (document.getElementById('call-overlay') && document.getElementById('call-overlay').classList.contains('active'))
    );
    var strip = ensureStrip();
    strip.style.display = callVisible ? 'block' : 'none';
    if (!callVisible) return;

    var emotion = currentEmotion();
    var item = emotionItems.find(function(x){ return x[0] === emotion; }) || emotionItems[5];
    document.querySelectorAll('#vivlos-emotion-strip .ves-item').forEach(function(el){
      el.classList.toggle('active', el.getAttribute('data-emotion') === emotion);
    });
    var label = document.getElementById('ves-current-label');
    if (label) label.textContent = item[2];
  }

  var css = document.createElement('style');
  css.id = 'vivlos-emotion-strip-style';
  css.textContent = `
    #vivlos-emotion-strip {
      display:none; position:fixed; z-index:99990;
      left:50%; bottom:94px; transform:translateX(-50%);
      width:min( min(720px, calc(100vw - 28px)), 94vw);
      padding:10px 13px 11px; box-sizing:border-box;
      color:#eaf6ff; background:rgba(5,18,31,.94);
      border:1px solid rgba(64,185,255,.34); border-radius:16px;
      box-shadow:0 8px 30px rgba(0,0,0,.35);
      backdrop-filter:blur(12px); -webkit-backdrop-filter:blur(12px);
      font-family:inherit; pointer-events:none;
    }
    #vivlos-emotion-strip .ves-head {
      display:flex; align-items:center; gap:7px;
      font-size:9px; letter-spacing:1.5px; font-weight:800;
      color:#8fb6ca; margin:0 2px 8px;
    }
    #vivlos-emotion-strip .ves-live-dot {
      width:7px;height:7px;border-radius:50%;background:#27d89a;
      box-shadow:0 0 8px #27d89a; flex:none;
    }
    #vivlos-emotion-strip .ves-current-label {
      margin-left:auto; color:#6ed1ff; letter-spacing:0;
      font-size:11px; font-weight:700;
    }
    #vivlos-emotion-strip .ves-items {
      display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:5px;
    }
    #vivlos-emotion-strip .ves-item {
      min-width:0; display:flex; flex-direction:column; align-items:center;
      justify-content:center; gap:4px; padding:7px 2px 6px;
      border:1px solid rgba(110,160,190,.13); border-radius:10px;
      background:rgba(255,255,255,.035); opacity:.58;
      transition:background .18s,border-color .18s,opacity .18s,transform .18s;
    }
    #vivlos-emotion-strip .ves-item.active {
      opacity:1; background:rgba(0,166,232,.19);
      border-color:#20b9ff; transform:translateY(-2px);
      box-shadow:0 0 14px rgba(32,185,255,.18);
    }
    #vivlos-emotion-strip .ves-emoji {font-size:19px;line-height:1.1}
    #vivlos-emotion-strip .ves-name {
      font-size:9px; white-space:nowrap; overflow:hidden;
      text-overflow:ellipsis; color:#d5e9f5;
    }
    @media(max-width:520px) {
      #vivlos-emotion-strip {bottom:86px;padding:8px 7px 9px}
      #vivlos-emotion-strip .ves-items {gap:3px}
      #vivlos-emotion-strip .ves-item {padding:6px 1px 5px}
      #vivlos-emotion-strip .ves-emoji {font-size:17px}
      #vivlos-emotion-strip .ves-name {font-size:8px}
    }
  `;
  document.head.appendChild(css);

  function start(){
    render();
    if (stripTimer) clearInterval(stripTimer);
    stripTimer = setInterval(render, 350);
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }

  // Re-render immediately when call navigation changes.
  var _origNavToEmotion = window.navTo;
  if (typeof _origNavToEmotion === 'function') {
    window.navTo = function(page){
      var result = _origNavToEmotion.apply(this, arguments);
      setTimeout(render, 60);
      return result;
    };
  }
  var _origDNavToEmotion = window.dNavTo;
  if (typeof _origDNavToEmotion === 'function') {
    window.dNavTo = function(page){
      var result = _origDNavToEmotion.apply(this, arguments);
      setTimeout(render, 60);
      return result;
    };
  }
  window.updateVivlosEmotionStrip = render;
})();
