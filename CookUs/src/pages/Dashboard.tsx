

type DashboardProps = { isLoggedIn?: boolean }
export default function Dashboard({ isLoggedIn = false }: DashboardProps) {
  return isLoggedIn ? <div>여기에 대시보드</div> : <div style={{opacity:.7}}>로그인 후 이용할 수 있어요.</div>
}
