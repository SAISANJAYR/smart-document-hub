import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

/* Interface strings in English and Malayalam (USP 4 extends to the UI itself).
   Missing Malayalam keys fall back to English. */
const STRINGS = {
  en: {
    'nav.dashboard': 'Dashboard', 'nav.library': 'Documents', 'nav.ask': 'Ask', 'nav.search': 'Search',
    'nav.calendar': 'Calendar', 'nav.graph': 'Graph', 'nav.history': 'History',
    'status.online': 'Online', 'status.offline': 'Offline',
    'auth.signin': 'Sign in', 'auth.signout': 'Sign out', 'auth.register': 'Create account',

    'landing.title': 'Ask your documents, in your language.',
    'landing.lede': 'Upload circulars, contracts and scanned notices in English or Malayalam. Smart Document Hub reads them, finds the deadlines, links related files, and answers questions with the exact passage it used.',
    'landing.open': 'Open the workspace', 'landing.demo': 'Try the demo account',
    'landing.problem': 'An officer should not have to read every file to find one date',
    'landing.problemBody': 'Deadlines sit in paragraph four of a circular. The same contractor appears in three files nobody has linked. Half the notices are in Malayalam, the search box only understands English. Smart Document Hub does the reading, and shows its working.',
    'landing.how': 'What happens when you upload',
    'landing.does': 'Four things it does',

    'dash.greeting.morning': 'Good morning', 'dash.greeting.afternoon': 'Good afternoon', 'dash.greeting.evening': 'Good evening',
    'dash.sub': 'Here is what your documents are telling you.',
    'dash.documents': 'Documents', 'dash.processed': 'processed', 'dash.deadlines': 'Upcoming deadlines', 'dash.urgent': 'need attention this week',
    'dash.connections': 'Connections', 'dash.connectionsSub': 'between related files', 'dash.questions': 'Questions asked', 'dash.questionsSub': 'with cited answers',
    'dash.recent': 'Recent documents', 'dash.coming': 'Coming up', 'dash.ask': 'Ask your documents', 'dash.askPh': 'e.g. When is the last date to submit utilisation certificates?',
    'dash.system': 'System',

    'ask.scope': 'Documents in scope', 'ask.all': 'All documents', 'ask.answerIn': 'Answer in', 'ask.auto': 'Auto',
    'ask.question': 'Your question', 'ask.placeholder': 'Ask about your documents, in English or Malayalam…',
    'ask.run': 'Ask', 'ask.running': 'Thinking…', 'ask.try': 'Try one of these', 'ask.answer': 'Answer',
    'ask.confidence': 'Confidence', 'ask.sources': 'Sources', 'ask.how': 'How the system answered',
    'ask.howEmpty': 'Each step the system takes to answer — language detection, retrieval, generation, checking — will be listed here with its timing.',
    'ask.copy': 'Copy answer', 'ask.trace': 'Download trace (JSON)', 'ask.another': 'Ask another question',
    'ask.lowConf': 'Low confidence', 'ask.lowConfBody': 'The retrieved passages only partly match the question. Check the sources before relying on this answer.',
    'ask.readAs': 'Read as', 'ask.engine': 'Engine',

    'lib.title': 'Documents', 'lib.sub': 'Every file you upload is read, translated if needed, tagged, and linked to the rest.',
    'lib.drop': 'Drop files here, or', 'lib.browse': 'browse files', 'lib.hint': 'PDF, DOCX, TXT, PNG or JPG · up to 50 MB · English or Malayalam',

    'search.title': 'Search', 'search.ph': 'Search by meaning, keyword or tag…', 'search.tags': 'Filter by tag',
    'cal.title': 'Calendar', 'cal.sub': 'Dates and deadlines found inside your documents, classified by what they mean.',
    'graph.title': 'Knowledge graph', 'graph.sub': 'Documents that talk about the same things are linked. Line weight is semantic similarity.',
    'history.title': 'History', 'history.sub': 'Every question asked, with its answer and how it was produced.',
  },
  ml: {
    'nav.dashboard': 'ഡാഷ്ബോർഡ്', 'nav.library': 'രേഖകൾ', 'nav.ask': 'ചോദിക്കുക', 'nav.search': 'തിരയുക',
    'nav.calendar': 'കലണ്ടർ', 'nav.graph': 'ബന്ധങ്ങൾ', 'nav.history': 'ചരിത്രം',
    'status.online': 'ഓൺലൈൻ', 'status.offline': 'ഓഫ്‌ലൈൻ',
    'auth.signin': 'ലോഗിൻ', 'auth.signout': 'ലോഗ് ഔട്ട്', 'auth.register': 'അക്കൗണ്ട് സൃഷ്ടിക്കുക',

    'landing.title': 'നിങ്ങളുടെ രേഖകളോട്, നിങ്ങളുടെ ഭാഷയിൽ ചോദിക്കൂ.',
    'landing.lede': 'ഇംഗ്ലീഷിലോ മലയാളത്തിലോ ഉള്ള സർക്കുലറുകൾ, കരാറുകൾ, സ്കാൻ ചെയ്ത നോട്ടീസുകൾ അപ്‌ലോഡ് ചെയ്യുക. സ്മാർട്ട് ഡോക്യുമെന്റ് ഹബ് അവ വായിച്ച്, സമയപരിധികൾ കണ്ടെത്തി, ബന്ധപ്പെട്ട ഫയലുകൾ ബന്ധിപ്പിച്ച്, ഉപയോഗിച്ച ഭാഗം സഹിതം ഉത്തരം നൽകുന്നു.',
    'landing.open': 'വർക്ക്‌സ്‌പേസ് തുറക്കുക', 'landing.demo': 'ഡെമോ അക്കൗണ്ട് പരീക്ഷിക്കുക',
    'landing.problem': 'ഒരു തീയതി കണ്ടെത്താൻ ഒരു ഉദ്യോഗസ്ഥൻ എല്ലാ ഫയലുകളും വായിക്കേണ്ടതില്ല',
    'landing.how': 'അപ്‌ലോഡ് ചെയ്യുമ്പോൾ എന്ത് സംഭവിക്കുന്നു',
    'landing.does': 'ഇത് ചെയ്യുന്ന നാല് കാര്യങ്ങൾ',

    'dash.greeting.morning': 'സുപ്രഭാതം', 'dash.greeting.afternoon': 'നമസ്കാരം', 'dash.greeting.evening': 'ശുഭസായാഹ്നം',
    'dash.sub': 'നിങ്ങളുടെ രേഖകൾ പറയുന്നത് ഇതാ.',
    'dash.documents': 'രേഖകൾ', 'dash.processed': 'പ്രോസസ്സ് ചെയ്തു', 'dash.deadlines': 'വരാനിരിക്കുന്ന സമയപരിധികൾ', 'dash.urgent': 'ഈ ആഴ്ച ശ്രദ്ധിക്കേണ്ടവ',
    'dash.connections': 'ബന്ധങ്ങൾ', 'dash.connectionsSub': 'ബന്ധപ്പെട്ട ഫയലുകൾക്കിടയിൽ', 'dash.questions': 'ചോദിച്ച ചോദ്യങ്ങൾ', 'dash.questionsSub': 'ഉറവിടം സഹിതം',
    'dash.recent': 'സമീപകാല രേഖകൾ', 'dash.coming': 'വരാനിരിക്കുന്നവ', 'dash.ask': 'നിങ്ങളുടെ രേഖകളോട് ചോദിക്കുക', 'dash.askPh': 'ഉദാ: യൂട്ടിലൈസേഷൻ സർട്ടിഫിക്കറ്റ് സമർപ്പിക്കാനുള്ള അവസാന തീയതി എപ്പോഴാണ്?',
    'dash.system': 'സിസ്റ്റം',

    'ask.scope': 'പരിഗണിക്കുന്ന രേഖകൾ', 'ask.all': 'എല്ലാ രേഖകളും', 'ask.answerIn': 'ഉത്തരത്തിന്റെ ഭാഷ', 'ask.auto': 'സ്വയം',
    'ask.question': 'നിങ്ങളുടെ ചോദ്യം', 'ask.placeholder': 'ഇംഗ്ലീഷിലോ മലയാളത്തിലോ നിങ്ങളുടെ രേഖകളെക്കുറിച്ച് ചോദിക്കുക…',
    'ask.run': 'ചോദിക്കുക', 'ask.running': 'ആലോചിക്കുന്നു…', 'ask.try': 'ഇവയിലൊന്ന് പരീക്ഷിക്കുക', 'ask.answer': 'ഉത്തരം',
    'ask.confidence': 'വിശ്വാസ്യത', 'ask.sources': 'ഉറവിടങ്ങൾ', 'ask.how': 'സിസ്റ്റം ഉത്തരം കണ്ടെത്തിയത് എങ്ങനെ',
    'ask.howEmpty': 'ഭാഷ തിരിച്ചറിയൽ, തിരച്ചിൽ, ഉത്തരം തയ്യാറാക്കൽ, പരിശോധന — ഓരോ ഘട്ടവും സമയം സഹിതം ഇവിടെ കാണാം.',
    'ask.copy': 'ഉത്തരം പകർത്തുക', 'ask.trace': 'ട്രേസ് ഡൗൺലോഡ് (JSON)', 'ask.another': 'മറ്റൊരു ചോദ്യം',
    'ask.lowConf': 'കുറഞ്ഞ വിശ്വാസ്യത', 'ask.lowConfBody': 'കണ്ടെത്തിയ ഭാഗങ്ങൾ ചോദ്യവുമായി ഭാഗികമായി മാത്രമേ യോജിക്കുന്നുള്ളൂ. ആശ്രയിക്കുന്നതിന് മുമ്പ് ഉറവിടങ്ങൾ പരിശോധിക്കുക.',
    'ask.readAs': 'വായിച്ചത്', 'ask.engine': 'എഞ്ചിൻ',

    'lib.title': 'രേഖകൾ', 'lib.sub': 'നിങ്ങൾ അപ്‌ലോഡ് ചെയ്യുന്ന ഓരോ ഫയലും വായിച്ച്, ആവശ്യമെങ്കിൽ വിവർത്തനം ചെയ്ത്, ടാഗ് ചെയ്ത്, മറ്റുള്ളവയുമായി ബന്ധിപ്പിക്കുന്നു.',
    'lib.drop': 'ഫയലുകൾ ഇവിടെ ഇടുക, അല്ലെങ്കിൽ', 'lib.browse': 'ഫയലുകൾ തിരഞ്ഞെടുക്കുക', 'lib.hint': 'PDF, DOCX, TXT, PNG, JPG · 50 MB വരെ · ഇംഗ്ലീഷ് അല്ലെങ്കിൽ മലയാളം',

    'search.title': 'തിരയുക', 'search.ph': 'അർത്ഥം, വാക്ക് അല്ലെങ്കിൽ ടാഗ് ഉപയോഗിച്ച് തിരയുക…', 'search.tags': 'ടാഗ് ഉപയോഗിച്ച് ചുരുക്കുക',
    'cal.title': 'കലണ്ടർ', 'cal.sub': 'നിങ്ങളുടെ രേഖകൾക്കുള്ളിൽ കണ്ടെത്തിയ തീയതികളും സമയപരിധികളും.',
    'graph.title': 'നോളജ് ഗ്രാഫ്', 'graph.sub': 'ഒരേ കാര്യങ്ങളെക്കുറിച്ച് പറയുന്ന രേഖകൾ ബന്ധിപ്പിച്ചിരിക്കുന്നു.',
    'history.title': 'ചരിത്രം', 'history.sub': 'ചോദിച്ച ഓരോ ചോദ്യവും, അതിന്റെ ഉത്തരവും അത് തയ്യാറാക്കിയ വിധവും.',
  },
};

const LangContext = createContext({ lang: 'en', setLang: () => {}, t: (k) => k });

function initialLang() {
  try { return localStorage.getItem('sdh.lang') === 'ml' ? 'ml' : 'en'; } catch { return 'en'; }
}

export function LangProvider({ children }) {
  const [lang, setLangState] = useState(initialLang);
  useEffect(() => { document.documentElement.lang = lang; }, [lang]);
  const setLang = useCallback((l) => {
    setLangState(l);
    try { localStorage.setItem('sdh.lang', l); } catch { /* ignore */ }
  }, []);
  const t = useCallback((key) => STRINGS[lang][key] ?? STRINGS.en[key] ?? key, [lang]);
  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t]);
  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}

export const useLang = () => useContext(LangContext);
