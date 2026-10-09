export type User={id:number;email:string;name:string;role:'admin'|'faculty'|'student';faculty_id?:number;student_group_id?:string}
export type Session={id:number;course_offering_id:number;day:string;start_period:number;duration_periods:number;room_id:number;faculty_ids:number[];participant_group_ids:string[]}
const API='/api'
export const token=()=>localStorage.getItem('timetable_token')
export async function request<T>(path:string,init:RequestInit={}):Promise<T>{
  const headers=new Headers(init.headers); headers.set('Content-Type','application/json'); if(token())headers.set('Authorization',`Bearer ${token()}`)
  const response=await fetch(`${API}${path}`,{...init,headers})
  if(response.status===401){localStorage.removeItem('timetable_token');localStorage.removeItem('timetable_user')}
  if(!response.ok){let detail=`Request failed (${response.status})`;try{const body=await response.json();detail=body.detail||detail}catch{}throw new Error(detail)}
  return response.json()
}
export const login=(email:string,password:string)=>request<{access_token:string;user:User}>('/auth/login',{method:'POST',body:JSON.stringify({email,password})})
export const list=(resource:string)=>request<{items:any[];total:number}>(`/${resource}?page=1&page_size=100`)
export const create=(resource:string,data:unknown)=>request(`/${resource}`,{method:'POST',body:JSON.stringify(data)})
export const timetable=()=>request<{id:number;version:number;status:string;sessions:Session[]}>('/timetables/latest')

