// ══════════════════════════════════════════════
//  Vivlos v3 — i18n ПОЛНЫЙ (RU + KK)
// ══════════════════════════════════════════════
window.I18N = {
  ru: {
    // ── Login
    welcome:'Добро пожаловать',login_subtitle:'Войди в аккаунт или зарегистрируйся',
    tab_login:'Войти',tab_register:'Регистрация',
    email:'Email',password:'Пароль',
    field_name:'Имя',field_surname:'Фамилия',field_age:'Возраст',
    who_are_you:'Кто вы?',adult:'👤 Взрослый',kid:'🧒 Ребёнок',
    register_btn:'Создать аккаунт',login_btn:'Войти',
    ph_email:'you@mail.com',ph_password:'••••••••',
    ph_name:'Алия',ph_surname:'Иванова',ph_password_min:'Минимум 6 символов',
    tag_free:'🆓 Бесплатно',tag_secure:'🔒 Безопасно',tag_multilang:'🌐 Мультиязычно',
    // ── Nav
    nav_home:'Главная',nav_history:'История',nav_notifs:'Уведомления',
    nav_profile:'Профиль',nav_create:'Создать бота',nav_settings:'Настройки',logout:'Выйти',
    // ── Home
    greeting:'Добрый день! 👋',greeting_sub:'Выбери AI-компаньона для разговора',
    how_are_you:'Как ты сейчас?',search_placeholder:'Найти компаньона...',
    ai_companions:'AI-компаньоны',my_companions:'Мои персонажи',
    filter_all:'Все',filter_kids:'Для детей',filter_adults:'Для взрослых',
    filter_study:'Учёба',filter_support:'Поддержка',filter_my:'Мои',
    // ── Stats
    stat_calls:'Звонков',stat_minutes:'Минут',stat_streak:'Дней подряд',stat_awards:'Наград',
    // ── XP
    xp_level:'Уровень',xp_next:'до следующего',streak_label:'дней подряд',
    streak_today:'Позвони сегодня, чтобы не потерять серию!',
    levelup_title:'Новый уровень!',levelup_sub:'Ты достиг нового уровня. Так держать!',levelup_btn:'Ура! 🎉',
    // ── History
    hist_companion:'Компаньон',hist_message:'Последнее сообщение',hist_time:'Время',
    hist_duration:'Длительность',hist_empty:'Здесь появятся твои звонки',
    // ── Profile
    achievements:'Достижения',settings:'Настройки',
    ach_first_step:'Первый шаг',ach_7_days:'7 дней',ach_10_calls:'10 звонков',
    ach_hour:'Час общения',ach_study:'Учёба',ach_support:'Поддержка',
    ach_polyglot:'Полиглот',ach_master:'Мастер',ach_creator:'Создатель',ach_streak30:'Месяц подряд',
    ach_open_all:'Открыть все →',
    // ── Mini-games
    game_quiz:'Викторина',game_memory:'Мемори',game_word:'Угадай слово',
    game_quiz_sub:'7 вопросов',game_memory_sub:'Найди пары',game_word_sub:'Угадай слово',
    mini_games:'Мини-игры',
    // ── Notifications
    notif_refresh:'Обновить',notif_mark_read:'Все прочитаны',
    notif_loading:'Загрузка...',notif_empty:'Пока нет уведомлений',notif_error:'Ошибка загрузки',
    // ── Call
    call_end:'Завершить',video_call:'Видеозвонок',speak_listen:'🎙 Говорите — я слушаю...',call_btn:'Позвонить',
    // ── Emotions
    emo_happy:'Радость',emo_sad:'Грусть',emo_angry:'Злость',emo_surprised:'Удивление',
    emo_fearful:'Страх',emo_disgusted:'Недовольство',emo_neutral:'Спокойный',
    emo_excited:'Восторг',emo_tired:'Усталость',emo_focused:'Концентрация',
    emo_nervous:'Нервозность',emo_confused:'Растерянность',
    emo_bored:'Скука',emo_contempt:'Пренебрежение',emo_pensive:'Задумчивость',
    // ── Errors
    err_fill_fields:'Заполни все поля',err_login:'Ошибка входа',err_register:'Ошибка регистрации',
    cam_unavailable:'Камера недоступна',
    // ── Create agent
    create_title:'Создать AI-персонажа',create_name:'Имя персонажа',create_emoji:'Аватар',
    create_desc:'Описание и характер',create_desc_hint:'Опиши характер, привычки, манеру общения...',
    create_category:'Аудитория',create_voice:'Голос',create_color:'Цвет карточки',
    create_preview:'Предпросмотр',create_btn:'✦ Создать персонажа',create_success:'Персонаж создан!',
    create_my_agents:'Мои персонажи',create_empty:'Ты ещё не создавал персонажей',
    cat_kids:'Дети',cat_adults:'Взрослые',KIDS:'ДЕТИ',ADULTS:'18+',
    voice_warm:'Тёплый',voice_deep:'Глубокий',voice_calm:'Спокойный',voice_bright:'Яркий',voice_neutral:'Нейтральный',
    // ── Bot notif kinds
    kind_bot:'Сообщение от ИИ',kind_streak:'Серия',kind_achievement:'Достижение',
    kind_info:'Информация',kind_new:'Новое',
    // ── Settings
    set_title:'Настройки',set_profile:'Профиль',set_appearance:'Оформление',
    set_voice_audio:'Голос и аудио',set_notifications:'Уведомления',set_account:'Аккаунт',
    set_save:'Сохранить',set_saved:'✓ Сохранено!',
    set_display_name:'Имя в профиле',set_avatar:'Фото профиля',
    set_change_avatar:'Изменить фото',set_upload_avatar:'Загрузить фото',
    set_tts_enabled:'Голосовые ответы (TTS)',set_speech_enabled:'Распознавание речи',
    set_lang_ui:'Язык интерфейса',set_speech_lang:'Язык распознавания речи',
    set_notif_bot:'Сообщения от ботов',set_notif_streak:'Напоминания о серии',
    set_notif_ach:'Уведомления о достижениях',
    set_danger:'Опасная зона',set_clear_data:'Очистить все данные',
    set_clear_confirm:'Очистить историю и настройки?',
    theme_label:'Тема оформления',theme_pick:'Выбери цветовую тему',
    vosk_title:'Распознавание речи (Vosk)',vosk_kk:'Казахский (Vosk)',vosk_ru:'Русский (Vosk)',
    vosk_tip:'Пока Vosk не установлен — используется Web Speech API (онлайн, Chrome/Edge). Vosk работает оффлайн.',
    bot_avatars:'Аватары AI-компаньонов',
  },
  kk: {
    // ── Login
    welcome:'Қош келдіңіз',login_subtitle:'Аккаунтқа кіріңіз немесе тіркеліңіз',
    tab_login:'Кіру',tab_register:'Тіркелу',
    email:'Email',password:'Құпия сөз',
    field_name:'Аты',field_surname:'Тегі',field_age:'Жасы',
    who_are_you:'Сіз кімсіз?',adult:'👤 Ересек',kid:'🧒 Бала',
    register_btn:'Аккаунт жасау',login_btn:'Кіру',
    ph_email:'you@mail.com',ph_password:'••••••••',
    ph_name:'Аяша',ph_surname:'Иванова',ph_password_min:'Кемінде 6 таңба',
    tag_free:'🆓 Тегін',tag_secure:'🔒 Қауіпсіз',tag_multilang:'🌐 Көптілді',
    // ── Nav
    nav_home:'Басты бет',nav_history:'Тарих',nav_notifs:'Хабарламалар',
    nav_profile:'Профиль',nav_create:'Бот жасау',nav_settings:'Параметрлер',logout:'Шығу',
    // ── Home
    greeting:'Қайырлы күн! 👋',greeting_sub:'Сөйлесу үшін AI-серіктес таңда',
    how_are_you:'Қазір қалайсың?',search_placeholder:'Серіктес іздеу...',
    ai_companions:'AI-серіктестер',my_companions:'Менің кейіпкерлерім',
    filter_all:'Барлығы',filter_kids:'Балаларға',filter_adults:'Ересектерге',
    filter_study:'Оқу',filter_support:'Қолдау',filter_my:'Менікі',
    // ── Stats
    stat_calls:'Қоңырау',stat_minutes:'Минут',stat_streak:'Күн қатарынан',stat_awards:'Марапат',
    // ── XP
    xp_level:'Деңгей',xp_next:'келесіге дейін',streak_label:'күн қатарынан',
    streak_today:'Сериянды жалғастыру үшін бүгін қоңырау шал!',
    levelup_title:'Жаңа деңгей!',levelup_sub:'Жаңа деңгейге жеттің. Солай ұстан!',levelup_btn:'Ура! 🎉',
    // ── History
    hist_companion:'Серіктес',hist_message:'Соңғы хабарлама',hist_time:'Уақыт',
    hist_duration:'Ұзақтығы',hist_empty:'Мұнда қоңырауларың пайда болады',
    // ── Profile
    achievements:'Жетістіктер',settings:'Параметрлер',
    ach_first_step:'Алғашқы қадам',ach_7_days:'7 күн',ach_10_calls:'10 қоңырау',
    ach_hour:'Бір сағат',ach_study:'Оқу',ach_support:'Қолдау',
    ach_polyglot:'Полиглот',ach_master:'Шебер',ach_creator:'Жасаушы',ach_streak30:'Бір ай қатарынан',
    ach_open_all:'Барлығын ашу →',
    // ── Mini-games
    game_quiz:'Викторина',game_memory:'Жады ойыны',game_word:'Сөзді тап',
    game_quiz_sub:'7 сұрақ',game_memory_sub:'Жұптарды тап',game_word_sub:'Сөзді тап',
    mini_games:'Мини-ойындар',
    // ── Notifications
    notif_refresh:'Жаңарту',notif_mark_read:'Барлығын оқылды деп белгілеу',
    notif_loading:'Жүктелуде...',notif_empty:'Әзірге хабарлама жоқ',notif_error:'Жүктеу қатесі',
    // ── Call
    call_end:'Аяқтау',video_call:'Бейне қоңырау',speak_listen:'🎙 Сөйлеңіз — тыңдап тұрмын...',call_btn:'Қоңырау шалу',
    // ── Emotions
    emo_happy:'Қуанышты',emo_sad:'Мұңды',emo_angry:'Ашулы',emo_surprised:'Таңданған',
    emo_fearful:'Қорыққан',emo_disgusted:'Жиренген',emo_neutral:'Бейтарап',
    emo_excited:'Асып-тасыған',emo_tired:'Шаршаған',emo_focused:'Шоғырланған',
    emo_nervous:'Алаңдаған',emo_confused:'Шатасқан',
    emo_bored:'Зерігіп жатыр',emo_contempt:'Менсінбеген',emo_pensive:'Ойға батқан',
    // ── Errors
    err_fill_fields:'Барлық өрістерді толтырыңыз',err_login:'Кіру қатесі',
    err_register:'Тіркелу қатесі',cam_unavailable:'Камера қолжетімді емес',
    // ── Create agent
    create_title:'AI-кейіпкер жасау',create_name:'Кейіпкер аты',create_emoji:'Аватар',
    create_desc:'Сипаттама және мінез',create_desc_hint:'Мінезін, әдеттерін, сөйлеу мәнерін сипаттаңыз...',
    create_category:'Аудитория',create_voice:'Дауыс',create_color:'Карточка түсі',
    create_preview:'Алдын ала қарау',create_btn:'✦ Кейіпкер жасау',create_success:'Кейіпкер жасалды!',
    create_my_agents:'Менің кейіпкерлерім',create_empty:'Сіз әлі кейіпкер жасаған жоқсыз',
    cat_kids:'Балалар',cat_adults:'Ересектер',KIDS:'БАЛАЛАР',ADULTS:'18+',
    voice_warm:'Жылы',voice_deep:'Терең',voice_calm:'Тыныш',voice_bright:'Жарқын',voice_neutral:'Бейтарап',
    // ── Bot notif kinds
    kind_bot:'ИИ хабары',kind_streak:'Серия',kind_achievement:'Жетістік',
    kind_info:'Ақпарат',kind_new:'Жаңа',
    // ── Settings
    set_title:'Параметрлер',set_profile:'Профиль',set_appearance:'Безендіру',
    set_voice_audio:'Дауыс және дыбыс',set_notifications:'Хабарламалар',set_account:'Аккаунт',
    set_save:'Сақтау',set_saved:'✓ Сақталды!',
    set_display_name:'Профильдегі ат',set_avatar:'Профиль фотосы',
    set_change_avatar:'Фотоны өзгерту',set_upload_avatar:'Фото жүктеу',
    set_tts_enabled:'Дауыстық жауаптар (TTS)',set_speech_enabled:'Сөзді тану',
    set_lang_ui:'Интерфейс тілі',set_speech_lang:'Сөйлеуді тану тілі',
    set_notif_bot:'Боттардан хабарлар',set_notif_streak:'Серия еске салу',
    set_notif_ach:'Жетістік хабарламалары',
    set_danger:'Қауіпті аймақ',set_clear_data:'Барлық деректерді тазалау',
    set_clear_confirm:'Тарих пен параметрлерді тазалау?',
    theme_label:'Безендіру тақырыбы',theme_pick:'Түс тақырыбын таңда',
    vosk_title:'Сөзді тану (Vosk)',vosk_kk:'Қазақша (Vosk)',vosk_ru:'Орысша (Vosk)',
    vosk_tip:'Vosk орнатылмаса — Web Speech API қолданылады (онлайн, Chrome/Edge). Vosk оффлайн жұмыс жасайды.',
    bot_avatars:'AI-серіктестер аватарлары',
  }
};

window._curLang = (function(){
  var s=localStorage.getItem('vivlos_lang'); if(s&&I18N[s]) return s;
  var n=(navigator.language||'ru').slice(0,2); return I18N[n]?n:'ru';
})();

window.tr = function(key,vars){
  var dict=I18N[window._curLang]||I18N.ru;
  var t=dict[key]||I18N.ru[key]||key;
  if(vars){ Object.keys(vars).forEach(function(k){ t=t.replace('{'+k+'}',vars[k]); }); }
  return t;
};

window.applyI18n = function(){
  document.querySelectorAll('[data-i18n]').forEach(function(el){
    var k=el.getAttribute('data-i18n'); var t=tr(k); if(t&&t!==k) el.textContent=t;
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(function(el){
    var k=el.getAttribute('data-i18n-placeholder'); var t=tr(k); if(t) el.setAttribute('placeholder',t);
  });
  document.documentElement.lang=window._curLang;
  document.querySelectorAll('[data-lang]').forEach(function(b){
    b.classList.toggle('on',b.getAttribute('data-lang')===window._curLang);
  });
  if(window.S) window.S.uiLang=window._curLang;
  // Update dynamic elements
  var gr=document.getElementById('dh-greet');
  if(gr) gr.textContent=(window.S&&window.S.user&&window.S.user.name)
    ? tr('greeting').replace('👋','')+'— '+window.S.user.name+'! 👋'
    : tr('greeting');
};

window.switchLang = function(lang){
  if(!I18N[lang]) return;
  window._curLang=lang;
  localStorage.setItem('vivlos_lang',lang);
  if(window.S){
    window.S.uiLang=lang;
    if(lang==='kk') window.S.speechLang='kk-KZ';
    else if(lang==='ru') window.S.speechLang='ru-RU';
    if(window.recognition) window.recognition.lang=window.S.speechLang;
  }
  applyI18n();
  // Перерендерим карточки агентов
  if(typeof window.renderAgentsDesktop==='function') window.renderAgentsDesktop(window._lastCat||'all');
  if(typeof window.renderAgentsMobile==='function') window.renderAgentsMobile(window._lastCat||'all');
  // Перерендерим XP бар и streak (динамические — не имеют data-i18n)
  if(typeof window._renderXPBar==='function') window._renderXPBar();
  if(typeof window._renderStreak==='function') window._renderStreak();
  // Перерисовываем stat labels вручную
  var statMap={stat_calls:'stat_calls',stat_minutes:'stat_minutes',stat_streak:'stat_streak',stat_awards:'stat_awards'};
  // Обновить аватары ботов
  if(typeof window._renderBotAvatarSettings==='function') window._renderBotAvatarSettings();
  // Перегрузить уведомления
  var np=document.getElementById('dp-notifs');
  if(np&&np.classList.contains('active')&&typeof window.loadNotifications==='function') window.loadNotifications();
  // Обновить заголовок страницы
  var th=document.getElementById('dh-title');
  if(th){
    var pageNames={
      'dp-home':tr('nav_home'),'dp-history':tr('nav_history'),
      'dp-profile':tr('nav_profile'),'dp-notifs':tr('nav_notifs'),
      'dp-create':tr('nav_create'),'dp-settings':tr('nav_settings')
    };
    var active=document.querySelector('.page.active');
    if(active&&pageNames[active.id]) th.textContent=pageNames[active.id];
  }
  // Тема
  if(typeof window.renderThemeGrid==='function') window.renderThemeGrid('theme-grid-container');
  // Обновить кнопки языка
  document.querySelectorAll('[data-lang]').forEach(function(b){
    b.classList.toggle('on', b.getAttribute('data-lang')===lang);
  });
  // Синхронизируем селектор в настройках
  var langSel = document.getElementById('set-lang-ui');
  if(langSel) langSel.value = lang;
  // Синхронизируем язык распознавания речи
  var speechSel = document.getElementById('set-speech-lang');
  if(speechSel) speechSel.value = lang==='kk' ? 'kk-KZ' : lang==='en' ? 'en-US' : 'ru-RU';
};

document.addEventListener('DOMContentLoaded',function(){ applyI18n(); });