'use client';
import {useState} from 'react';
export default function useEditHistory<T>(initial:T){
  const [state,setState]=useState<{value:T;past:T[];future:T[];gesture?:T}>({value:initial,past:[],future:[]});
  const setValue=(update:(previous:T)=>T)=>setState(s=>{const value=update(s.value);return JSON.stringify(value)===JSON.stringify(s.value)?s:s.gesture!==undefined?{...s,value}:{value,past:[...s.past,s.value].slice(-80),future:[]};});
  const begin=()=>setState(s=>({...s,gesture:s.value}));
  const commit=()=>setState(s=>s.gesture===undefined?s:JSON.stringify(s.gesture)===JSON.stringify(s.value)?{...s,gesture:undefined}:{value:s.value,past:[...s.past,s.gesture].slice(-80),future:[]});
  const undo=()=>setState(s=>s.past.length?{value:s.past[s.past.length-1],past:s.past.slice(0,-1),future:[s.value,...s.future]}:s);
  const redo=()=>setState(s=>s.future.length?{value:s.future[0],past:[...s.past,s.value],future:s.future.slice(1)}:s);
  return {value:state.value,setValue,undo,redo,begin,commit,canUndo:!!state.past.length,canRedo:!!state.future.length};
}
