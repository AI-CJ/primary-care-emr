export function BrandMark({ className }: { className?: string }) {
  return <svg className={className} aria-hidden="true" focusable="false" viewBox="0 0 40 40" width="36" height="36">
    <rect width="40" height="40" rx="11" fill="#b7e5d6" />
    <path d="M17 7h6v10h10v6H23v10h-6V23H7v-6h10Z" fill="#176451" />
    <path d="M9 20h6l3-5 4 10 3-5h6" fill="none" stroke="#fff" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
}

export function CareIllustration({ patient }: { patient: boolean }) {
  return <svg className="care-illustration" aria-hidden="true" focusable="false" viewBox="0 0 380 230" fill="none">
    {patient ? <>
      <path d="M0 174Q75 113 160 176T380 142V230H0Z" fill="#b9e4d8" />
      <path d="M0 206Q89 151 190 202T380 184V230H0Z" fill="#78baa8" />
      <circle cx="292" cy="54" r="31" fill="#f2c4ae" />
      <path d="M52 208V132M52 158Q11 148 22 112Q53 113 52 158M52 179Q88 163 85 132Q55 132 52 179" stroke="#216b56" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
      <rect x="116" y="36" width="148" height="167" rx="17" fill="#fff" stroke="#7db6a7" strokeWidth="2" />
      <rect x="151" y="25" width="78" height="24" rx="8" fill="#246c59" />
      <path d="M190 105C154 81 177 60 190 80C203 60 226 81 190 105Z" fill="#d58c70" />
      {[124, 146, 168].map(y => <g key={y}><circle cx="140" cy={y} r="5" fill="#246c59" /><path d={`M155 ${y}H239`} stroke="#a8c9c1" strokeWidth="6" strokeLinecap="round" /></g>)}
      <path d="M309 197v-77m0 32q-30-7-31-38q31 1 31 38m0 25q32-11 34-41q-30 2-34 41" stroke="#216b56" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
    </> : <>
      <path d="M0 200Q82 103 184 168T380 112V230H0Z" fill="#174d49" />
      <path d="M0 223Q108 145 190 203T380 174V230H0Z" fill="#23645c" />
      <path d="M0 190Q120 121 232 191T380 137" stroke="#d58c70" strokeWidth="2" opacity=".8" />
      <rect x="28" y="19" width="298" height="169" rx="12" fill="#233f45" stroke="#76c5b5" strokeWidth="1.5" />
      <path d="M28 46H326M107 46V188" stroke="#527d7a" />
      <circle cx="42" cy="33" r="3" fill="#d58c70" /><circle cx="54" cy="33" r="3" fill="#90d7c5" />
      {[64, 86, 108, 130, 152].map((y,i) => <rect key={y} x="42" y={y} width={i===0?50:39} height="8" rx="4" fill={i===0?"#8ed4c3":"#527d7a"} />)}
      <circle cx="136" cy="75" r="13" fill="#8ed4c3" />
      <path d="M158 69h78m-78 13h47" stroke="#87a9a7" strokeWidth="6" strokeLinecap="round" />
      <rect x="123" y="104" width="186" height="66" rx="8" fill="#163337" stroke="#527d7a" />
      <path d="M134 138h29l11-13 13 29 17-40 13 24h26l9-10 10 10h35" stroke="#92e0c9" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
      <rect x="270" y="151" width="84" height="63" rx="10" fill="#d9f0e9" />
      <path d="M282 190h9v-14h-9Zm16 0h9v-22h-9Zm16 0h9v-32h-9Zm16 0h9v-18h-9Z" fill="#26735f" />
    </>}
  </svg>
}
