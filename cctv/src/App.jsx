import { useEffect, useRef, useState } from 'react'
import './App.css'
import { API_BASE_URL, fetchJson, parseEventJson } from './api'

const API = API_BASE_URL
const navItems = [
  ['dashboard', '◈', 'Dashboard'], ['monitoring', '▣', 'Live Monitoring'], ['webcam', '◎', 'Laptop Webcam'], ['attendance', '◷', 'Attendance'],
  ['students', '♙', 'Students / Employees'], ['cameras', '▤', 'Cameras'], ['safety', '△', 'Safety Events'],
  ['zones', '⬡', 'Restricted Zones'], ['alerts', '!', 'Alerts'], ['incidents', '◆', 'Incidents'],
  ['recordings', '▶', 'Recordings'], ['reports', '▥', 'Reports'], ['analytics', '⌁', 'Analytics'], ['settings', '⚙', 'Settings'],
]

function StatusDot({ status }) { return <span className={`status-dot ${status || 'unknown'}`} aria-label={status || 'unknown'} /> }
function titleFor(page) { return navItems.find(([key]) => key === page)?.[2] || 'Dashboard' }

function App() {
  const [page, setPage] = useState('dashboard')
  const [cameras, setCameras] = useState([])
  const [alerts, setAlerts] = useState([])
  const [students, setStudents] = useState([])
  const [attendance, setAttendance] = useState([])
  const [message, setMessage] = useState('Connecting to operations backend...')
  const [authenticated, setAuthenticated] = useState(false)

  async function loadData() {
    const responses = await Promise.all([
      fetchJson(`${API}/api/cameras`), fetchJson(`${API}/api/alerts`),
      fetchJson(`${API}/api/students`), fetchJson(`${API}/api/attendance`),
    ])
    setCameras(responses[0].data || []); setAlerts(responses[1].data || [])
    setStudents(responses[2].data || []); setAttendance(responses[3].data || [])
    setMessage('Operations backend connected')
  }

  useEffect(() => {
    if (!authenticated) return undefined
    const load = () => loadData().catch((error) => setMessage(error.message))
    window.setTimeout(load, 0)
    const source = new EventSource(`${API}/api/events`)
    source.addEventListener('system', (event) => {
      const data = parseEventJson(event)
      if (data) { setCameras(data.cameras || []); setAlerts(data.alerts || []); setMessage('Live operations link healthy') }
    })
    source.onerror = () => setMessage('Live feed disconnected. Retrying...')
    return () => source.close()
  }, [authenticated])

  async function addStudent(payload) { const photo = payload.photo; delete payload.photo; const result = await fetchJson(`${API}/api/students`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); if (photo) await fetchJson(`${API}/api/students/${result.data.id}/face`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image: photo }) }); await loadData() }
  async function deleteStudent(id) { await fetchJson(`${API}/api/students/${id}`, { method: 'DELETE' }); await loadData() }
  async function cameraAction(camera, action) { await fetchJson(`${API}/api/cameras/${camera.id}/${action}`, { method: 'POST' }); await loadData() }

  const online = cameras.filter((camera) => ['live', 'healthy'].includes(camera.status)).length
  const activeAlerts = alerts.filter((alert) => alert.status !== 'RESOLVED')
  const critical = activeAlerts.filter((alert) => alert.severity === 'CRITICAL').length
  const stats = { online, activeAlerts: activeAlerts.length, critical, students: students.length, present: attendance.length }

  if (!authenticated) return <LoginPage onLogin={() => setAuthenticated(true)} />
  return <main className="command-shell">
    <aside className="sidebar"><div className="brand"><span className="brand-mark">P</span><div><strong>PRESENT SIR</strong><small>AI ATTENDANCE & SAFETY</small></div></div><nav>{navItems.map(([key, icon, label]) => <button key={key} className={page === key ? 'active' : ''} onClick={() => setPage(key)}><span>{icon}</span><b>{label}</b></button>)}</nav><div className="sidebar-footer"><span className="eyebrow">SYSTEM MODE</span><strong>OPERATIONS</strong><small>Role: administrator</small></div></aside>
    <section className="workspace"><header className="topbar"><div><span className="eyebrow">FACILITY / NORTH CAMPUS</span><h1>{titleFor(page)}</h1></div><div className="top-status"><StatusDot status="live" /><span>{message}</span><time>{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time></div></header><Page page={page} cameras={cameras} alerts={alerts} students={students} attendance={attendance} stats={stats} onAddStudent={addStudent} onDeleteStudent={deleteStudent} onCameraAction={cameraAction} /></section>
  </main>
}

function LoginPage({ onLogin }) {
  const [error, setError] = useState('')
  async function submit(event) {
    event.preventDefault()
    try {
      await fetchJson(`${API}/api/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(Object.fromEntries(new FormData(event.currentTarget))) })
      onLogin()
    } catch (loginError) { setError(loginError.message) }
  }
  return <main className="login-shell"><form className="login-card" onSubmit={submit}><span className="brand-mark">P</span><span className="eyebrow">SECURE OPERATIONS ACCESS</span><h1>PRESENT SIR</h1><p>AI ATTENDANCE & SAFETY PLATFORM</p><label>Username<input name="username" required autoComplete="username" placeholder="admin" /></label><label>Password<input name="password" type="password" required autoComplete="current-password" /></label>{error && <div className="camera-error">{error}</div>}<button className="primary submit" type="submit">Sign in</button><small>Use your authorized operations account.</small></form></main>
}

function Page({ page, cameras, alerts, students, attendance, stats, onAddStudent, onDeleteStudent, onCameraAction }) {
  if (page === 'students') return <StudentsPage students={students} attendance={attendance} onAdd={onAddStudent} onDelete={onDeleteStudent} />
  if (page === 'attendance') return <AttendancePage attendance={attendance} students={students} />
  if (page === 'webcam') return <AttendanceCameraPage />
  if (page === 'monitoring' || page === 'cameras') return <CameraPage cameras={cameras} onAction={onCameraAction} />
  if (page === 'safety' || page === 'alerts' || page === 'incidents') return <SafetyPage alerts={alerts} />
  if (page === 'reports') return <ReportsPage />
  if (page === 'zones') return <DataPage title="Restricted zones" endpoint="/api/zones" columns={['name', 'camera_name', 'zone_type', 'severity']} />
  if (page === 'recordings') return <DataPage title="Recordings" endpoint="/recordings" columns={['camera_name', 'event_type', 'status', 'started_at']} />
  if (page === 'settings') return <HealthPage />
  if (page === 'analytics') return <AnalyticsPage stats={stats} />
  return <DashboardPage stats={stats} cameras={cameras} alerts={alerts} />
}

function DashboardPage({ stats, cameras, alerts }) {
  return <><section className="kpis"><Kpi label="PEOPLE ON SITE" value="--" note="AI model required" /><Kpi label="PRESENT TODAY" value={stats.present} note="Attendance records" /><Kpi label="CAMERAS ONLINE" value={`${stats.online}/${cameras.length}`} note="Live health" good /><Kpi label="ACTIVE ALERTS" value={stats.activeAlerts} note={stats.critical ? `${stats.critical} critical` : 'No critical events'} critical={stats.critical > 0} /></section><div className="content-grid"><section className="monitor-panel"><SectionHead eyebrow="OPERATIONS OVERVIEW" title="Live coverage" /><div className="mini-grid">{cameras.slice(0, 4).map((camera) => <CameraTile key={camera.id} camera={camera} />)}{!cameras.length && <Empty text="No cameras configured" />}</div></section><SafetyList alerts={alerts} /></div></>
}
function Kpi({ label, value, note, good, critical }) { return <div className="kpi"><span>{label}</span><strong>{value}</strong><em className={critical ? 'critical' : good ? 'good' : ''}>{note}</em></div> }
function SectionHead({ eyebrow, title, action }) { return <div className="section-head"><div><span className="eyebrow">{eyebrow}</span><h2>{title}</h2></div>{action}</div> }
function Empty({ text }) { return <div className="empty-state"><span className="empty-icon">□</span><h3>{text}</h3><p>There is no configured data for this view.</p></div> }

function CameraPage({ cameras, onAction }) { return <><SectionHead eyebrow="VISUAL COVERAGE" title="Camera wall" /><div className="camera-grid">{cameras.map((camera) => <CameraTile key={camera.id} camera={camera} onAction={onAction} />)}{!cameras.length && <Empty text="No cameras configured" />}</div></> }
function CameraTile({ camera, onAction }) { const live = ['live', 'healthy'].includes(camera.status); const [aiEnabled, setAiEnabled] = useState(Boolean(camera.ai_enabled)); async function snapshot() { await fetchJson(`${API}/api/cameras/${camera.id}/snapshot`, { method: 'POST' }) } async function toggleAi() { await fetchJson(`${API}/api/cameras/${camera.id}/features`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ai_enabled: !aiEnabled }) }); setAiEnabled(!aiEnabled) } return <article className="camera-tile"><div className="feed">{live ? <img src={`${API}/api/cameras/${camera.id}/stream`} alt={`Feed from ${camera.name}`} /> : <div className="feed-offline"><span>◌</span><strong>{(camera.status || 'STOPPED').toUpperCase()}</strong><small>{camera.last_error || 'Start camera to establish a feed'}</small></div>}<div className="tile-top"><span><StatusDot status={live ? 'live' : camera.status} /> {live ? 'LIVE' : (camera.status || 'STOPPED').toUpperCase()}</span><span>CAM-{String(camera.id).padStart(2, '0')}</span></div></div><div className="tile-info"><div><h3>{camera.name}</h3><p>{camera.location || 'Location not set'} · {camera.department || 'Unassigned'}</p></div></div><div className="tile-actions"><button onClick={() => onAction?.(camera, live ? 'stop' : 'start')}>{live ? 'Stop' : 'Start'}</button><button onClick={() => snapshot().catch(() => {})}>Snapshot</button><button onClick={() => toggleAi().catch(() => {})}>AI {aiEnabled ? 'on' : 'off'}</button></div></article> }

function StudentsPage({ students, attendance, onAdd, onDelete }) { const [show, setShow] = useState(false); const [query, setQuery] = useState(''); const filtered = students.filter((student) => `${student.name} ${student.register_number} ${student.department}`.toLowerCase().includes(query.toLowerCase())); return <><SectionHead eyebrow="WORKFORCE DIRECTORY" title="Students / employees" action={<button className="primary" onClick={() => setShow(true)}>＋ Add student</button>} /><div className="table-tools"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search name, ID, department" /></div><div className="data-table"><table><thead><tr><th>ID</th><th>Name</th><th>Department</th><th>Year / course</th><th>Attendance</th><th>Actions</th></tr></thead><tbody>{filtered.map((student) => <tr key={student.id}><td>{student.register_number}</td><td><strong>{student.name}</strong></td><td>{student.department}</td><td>{student.year} / {student.section}</td><td>{attendance.filter((item) => item.student_id === student.id).length} records</td><td><button className="text-button" onClick={() => onDelete(student.id)}>Delete</button></td></tr>)}{!filtered.length && <tr><td colSpan="6"><Empty text="No students found" /></td></tr>}</tbody></table></div>{show && <StudentModal onClose={() => setShow(false)} onSave={async (payload) => { await onAdd(payload); setShow(false) }} />}</> }
function StudentModal({ onClose, onSave }) { const [error, setError] = useState(''); async function submit(event) { event.preventDefault(); const form = event.currentTarget; const payload = Object.fromEntries(new FormData(form)); if (!payload.name || !payload.register_number) { setError('Student ID and name are required.'); return } const file = form.elements.photo.files[0]; if (file) { if (!file.type.startsWith('image/')) { setError('Please select a valid image file.'); return } payload.photo = await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = reject; reader.readAsDataURL(file) }) } try { await onSave(payload) } catch (err) { setError(err.message) } } return <div className="modal-backdrop"><form className="camera-form" onSubmit={submit}><button className="close" type="button" onClick={onClose}>×</button><span className="eyebrow">WORKFORCE DIRECTORY</span><h2>Add student</h2><label>Student / employee ID<input name="register_number" required placeholder="STU-001" /></label><label>Name<input name="name" required placeholder="Full name" /></label><div className="form-row"><label>Department<input name="department" placeholder="Production" /></label><label>Course / designation<input name="section" placeholder="Engineering" /></label></div><div className="form-row"><label>Year / shift<input name="year" placeholder="Year 2 / Shift A" /></label><label>Phone<input name="phone" /></label></div><label>Email<input name="email" type="email" /></label><label>Face photo<input name="photo" type="file" accept="image/png,image/jpeg" capture="user" /></label>{error && <small className="tile-error">{error}</small>}<button className="primary submit" type="submit">Save student</button></form></div> }

function AttendancePage({ attendance, students }) { const present = attendance.length; return <><section className="kpis"><Kpi label="TODAY'S DATE" value={new Date().toLocaleDateString()} note="Local facility time" /><Kpi label="PRESENT" value={present} note="Recorded entries" good /><Kpi label="ABSENT" value={Math.max(students.length - present, 0)} note="No entry today" /><Kpi label="UNKNOWN" value="--" note="Identification disabled" /></section><SectionHead eyebrow="WORKFORCE OPERATIONS" title="Attendance records" action={<div className="toolbar"><a className="primary" href={`${API}/export-csv`}>Export CSV</a><a className="primary" href={`${API}/export-excel`}>Export Excel</a></div>} /><div className="data-table"><table><thead><tr><th>ID</th><th>Name</th><th>Date</th><th>Entry time</th><th>Status</th><th>Camera</th><th>Confidence</th></tr></thead><tbody>{attendance.map((item) => <tr key={item.id}><td>{item.register_number}</td><td>{item.name}</td><td>{item.attendance_date}</td><td>{item.attendance_time}</td><td><span className="table-status">{item.status}</span></td><td>{item.camera_id}</td><td>{item.confidence}%</td></tr>)}{!attendance.length && <tr><td colSpan="7"><Empty text="No attendance records found" /></td></tr>}</tbody></table></div></> }

function SafetyPage({ alerts }) { return <><SectionHead eyebrow="SAFETY OPERATIONS" title="Safety events" /><div className="event-summary"><Kpi label="ACTIVE EVENTS" value={alerts.filter((a) => a.status !== 'RESOLVED').length} note="Requires review" critical /><Kpi label="CRITICAL" value={alerts.filter((a) => a.severity === 'CRITICAL').length} note="Immediate attention" critical /><Kpi label="RESOLVED" value={alerts.filter((a) => a.status === 'RESOLVED').length} note="Closed events" good /></div><SafetyList alerts={alerts} /></> }
function SafetyList({ alerts }) { return <aside className="alert-panel"><SectionHead eyebrow="SAFETY OPERATIONS" title="Active events" /><div className="alert-list">{alerts.length ? alerts.map((alert) => <article className={`alert-item ${alert.severity?.toLowerCase()}`} key={alert.id}><div className="alert-icon">{alert.severity === 'CRITICAL' ? '!' : '△'}</div><div><strong>{(alert.alert_type || 'EVENT').replaceAll('_', ' ')}</strong><p>{alert.description}</p><small>{alert.camera_location || 'Unassigned'} · {alert.status}</small></div></article>) : <div className="quiet-state"><span>✓</span><strong>All clear</strong><p>No safety events recorded.</p></div>}</div></aside> }
function ReportsPage() { return <><SectionHead eyebrow="REPORT CENTER" title="Reports" /><div className="report-grid">{[['Attendance report', 'Attendance records and daily totals', 'export-excel'], ['Safety report', 'Safety events and severity summary', 'export-csv'], ['PDF attendance report', 'Printable attendance report', 'export-pdf'], ['CSV data export', 'Portable filtered operations data', 'export-csv']].map(([title, text, endpoint]) => <article className="report-card" key={title}><span className="report-icon">▤</span><h3>{title}</h3><p>{text}</p><a className="primary" href={`${API}/${endpoint}`}>Export file</a></article>)}</div><div className="notice">Exports use the active backend session and current report filters.</div></> }
function DataPage({ title, endpoint, columns }) { const [rows, setRows] = useState([]); const [error, setError] = useState('Loading...'); useEffect(() => { fetchJson(`${API}${endpoint}`).then((body) => { setRows(body.data || []); setError('') }).catch((loadError) => setError(loadError.message)) }, [endpoint]); return <><SectionHead eyebrow="OPERATIONS DATA" title={title} /><div className="data-table"><table><thead><tr>{columns.map((column) => <th key={column}>{column.replaceAll('_', ' ')}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={row.id || index}>{columns.map((column) => <td key={column}>{String(row[column] ?? 'Not set')}</td>)}</tr>)}{!rows.length && <tr><td colSpan={columns.length}><Empty text={error || `No ${title.toLowerCase()} found`} /></td></tr>}</tbody></table></div></> }
function HealthPage() { const [health, setHealth] = useState(null); useEffect(() => { fetchJson(`${API}/api/health`).then(setHealth).catch(() => setHealth({ status: 'offline', application: 'offline', database: 'offline', ai: 'offline', storage: 'unknown' })) }, []); return <><SectionHead eyebrow="SYSTEM CONFIGURATION" title="System health" /><div className="health-grid">{Object.entries(health || { status: 'loading' }).map(([key, value]) => <div className="report-card" key={key}><span className="eyebrow">{key.toUpperCase()}</span><h3 className={value === 'healthy' ? 'good' : ''}>{String(value).toUpperCase()}</h3><p>Service status reported by the backend.</p></div>)}</div></> }
function AnalyticsPage({ stats }) { return <><SectionHead eyebrow="OPERATIONS ANALYTICS" title="Analytics" /><section className="kpis"><Kpi label="STUDENTS / EMPLOYEES" value={stats.students} note="Directory records" /><Kpi label="ATTENDANCE RECORDS" value={stats.present} note="Current dataset" good /><Kpi label="SAFETY EVENTS" value={stats.activeAlerts} note="Active review queue" critical={stats.critical > 0} /></section><div className="notice">Analytics are calculated from the records currently available in the connected database. No synthetic metrics are generated.</div></> }

function AttendanceCameraPage() {
  const videoRef = useRef(null); const streamRef = useRef(null); const recognitionRef = useRef(null)
  const [status, setStatus] = useState('OFFLINE'); const [sessionActive, setSessionActive] = useState(false); const [error, setError] = useState(''); const [result, setResult] = useState(null); const [devices, setDevices] = useState([]); const [deviceId, setDeviceId] = useState('')
  async function enumerateCameras() { if (!navigator.mediaDevices?.enumerateDevices) throw new Error('This browser does not support camera selection.'); const all = await navigator.mediaDevices.enumerateDevices(); const cameras = all.filter((device) => device.kind === 'videoinput'); setDevices(cameras); if (!deviceId && cameras[0]) setDeviceId(cameras[0].deviceId); if (!cameras.length) throw new Error('No compatible camera was detected.') }
  async function start() { setError(''); try { if (!navigator.mediaDevices?.getUserMedia) throw new Error('This browser does not support laptop camera access.'); await enumerateCameras(); const stream = await navigator.mediaDevices.getUserMedia({ video: deviceId ? { deviceId: { exact: deviceId } } : true, audio: false }); streamRef.current = stream; videoRef.current.srcObject = stream; await videoRef.current.play(); setStatus('LIVE'); } catch (cameraError) { setStatus(cameraError.name === 'NotAllowedError' ? 'PERMISSION DENIED' : 'ERROR'); setError(cameraError.name === 'NotAllowedError' ? 'Camera permission was denied. Please allow camera access in your browser settings.' : cameraError.name === 'NotReadableError' ? 'The camera is currently being used by another application.' : cameraError.message || 'Unable to access the camera.') } }
  function stop() { stopSession(); streamRef.current?.getTracks().forEach((track) => track.stop()); streamRef.current = null; if (videoRef.current) videoRef.current.srcObject = null; setStatus('OFFLINE') }
  function frame() { if (!videoRef.current?.videoWidth) return null; const canvas = document.createElement('canvas'); canvas.width = Math.min(videoRef.current.videoWidth, 960); canvas.height = Math.round(canvas.width * videoRef.current.videoHeight / videoRef.current.videoWidth); canvas.getContext('2d').drawImage(videoRef.current, 0, 0, canvas.width, canvas.height); return canvas.toDataURL('image/jpeg', .78) }
  function startSession() { if (status !== 'LIVE') { setError('Start the laptop camera first.'); return } if (recognitionRef.current) return; const controller = { stopped: false, timer: null }; recognitionRef.current = controller; let candidate = { id: null, count: 0 }; const scan = async () => { const image = frame(); if (!image || controller.stopped) return; try { const body = await fetchJson(`${API}/api/attendance/recognize`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image, confirm: false }), timeout: 5000 }); const data = body.data; setResult(data); if (data.status === 'RECOGNIZED' && candidate.id === data.student_id) candidate.count += 1; else candidate = { id: data.student_id, count: data.status === 'RECOGNIZED' ? 1 : 0 }; if (candidate.count >= 3 && data.status === 'RECOGNIZED' && !controller.stopped) { const confirmed = await fetchJson(`${API}/api/attendance/recognize`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image, confirm: true }), timeout: 5000 }); setResult(confirmed.data); candidate = { id: null, count: 0 }; } } catch (recognitionError) { if (recognitionError.code === 'TIMEOUT') setError('Recognition service timed out. Try a smaller camera resolution or check the backend.'); else setError(recognitionError.message) } finally { if (!controller.stopped) controller.timer = window.setTimeout(scan, 700) } }; scan(); setSessionActive(true); setError('') }
  function stopSession() { if (recognitionRef.current) { recognitionRef.current.stopped = true; window.clearTimeout(recognitionRef.current.timer) } recognitionRef.current = null; setSessionActive(false) }
  useEffect(() => () => { streamRef.current?.getTracks().forEach((track) => track.stop()); if (recognitionRef.current) clearInterval(recognitionRef.current) }, [])
  return <section className="webcam-page"><SectionHead eyebrow="FACE RECOGNITION ATTENDANCE" title="Live attendance camera" action={<span className={status === 'LIVE' ? 'good' : 'critical'}><StatusDot status={status === 'LIVE' ? 'live' : 'offline'} /> {status}</span>} /><div className="webcam-layout"><div className="webcam-preview"><video ref={videoRef} muted playsInline /><div className="video-label"><StatusDot status={status === 'LIVE' ? 'live' : 'offline'} /> {status} · Laptop / USB device</div></div><div className="webcam-controls"><label>SELECT CAMERA<select value={deviceId} onChange={(event) => setDeviceId(event.target.value)}><option value="">Default laptop webcam</option>{devices.map((device, index) => <option key={device.deviceId} value={device.deviceId}>{device.label || `Camera ${index + 1}`}</option>)}</select></label><div className="control-grid"><button className="primary" onClick={start}>Start live camera</button><button onClick={stop}>Stop camera</button><button className="primary" onClick={startSession}>{sessionActive ? 'Session active' : 'Start attendance'}</button><button onClick={stopSession}>Stop attendance</button></div>{result && <div className={`recognition-result ${result.status === 'RECOGNIZED' ? 'recognized' : ''}`}><strong>{result.confirmed ? '✓ ATTENDANCE VERIFIED' : result.status === 'RECOGNIZED' ? 'MATCH PENDING CONFIRMATION' : 'UNKNOWN PERSON'}</strong><span>{result.name || 'No registered match'}</span><small>{result.register_number || ''} {result.confidence != null ? `· Match ${result.confidence}%` : ''}</small><em>{result.attendance_status || result.message}</em></div>}{error && <div className="camera-error">{error}</div>}<p className="muted-note">Recognition samples one frame every 700 ms. Attendance is created only after three consistent matches and a registered face embedding.</p></div></div></section>
}

function WebcamPage() {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const recorderRef = useRef(null)
  const chunksRef = useRef([])
  const [devices, setDevices] = useState([])
  const [deviceId, setDeviceId] = useState('')
  const [status, setStatus] = useState('STOPPED')
  const [error, setError] = useState('')
  const [captureUrl, setCaptureUrl] = useState('')

  async function listDevices() {
    if (!navigator.mediaDevices?.enumerateDevices) throw new Error('This browser does not support camera device selection.')
    const entries = await navigator.mediaDevices.enumerateDevices()
    const videoDevices = entries.filter((entry) => entry.kind === 'videoinput')
    setDevices(videoDevices)
    if (!deviceId && videoDevices[0]) setDeviceId(videoDevices[0].deviceId)
    if (!videoDevices.length) throw new Error('No compatible camera was detected.')
  }

  async function start() {
    setError('')
    try {
      if (!navigator.mediaDevices?.getUserMedia) throw new Error('This browser does not support laptop camera access.')
      await listDevices()
      const stream = await navigator.mediaDevices.getUserMedia({ video: deviceId ? { deviceId: { exact: deviceId } } : true, audio: false })
      streamRef.current = stream
      videoRef.current.srcObject = stream
      await videoRef.current.play()
      setStatus('LIVE')
      await listDevices()
    } catch (cameraError) {
      const message = cameraError.name === 'NotAllowedError' ? 'Camera permission was denied. Please allow camera access in your browser settings.' : cameraError.name === 'NotReadableError' ? 'The camera is currently being used by another application.' : cameraError.message || 'Unable to access the camera.'
      setError(message); setStatus('ERROR')
    }
  }

  function stop() {
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
    setStatus('STOPPED')
  }

  function capture() {
    if (!videoRef.current?.videoWidth) { setError('Start the camera before capturing a photo.'); return }
    const canvas = document.createElement('canvas'); canvas.width = videoRef.current.videoWidth; canvas.height = videoRef.current.videoHeight
    canvas.getContext('2d').drawImage(videoRef.current, 0, 0)
    setCaptureUrl(canvas.toDataURL('image/jpeg', 0.92)); setError('')
  }

  function record() {
    if (!streamRef.current) { setError('Start the camera before recording.'); return }
    chunksRef.current = []
    const recorder = new MediaRecorder(streamRef.current)
    recorder.ondataavailable = (event) => event.data.size && chunksRef.current.push(event.data)
    recorder.onstop = () => setCaptureUrl(URL.createObjectURL(new Blob(chunksRef.current, { type: recorder.mimeType })))
    recorder.start(); recorderRef.current = recorder; setStatus('RECORDING')
  }

  function stopRecording() { recorderRef.current?.stop(); setStatus('LIVE') }
  useEffect(() => () => { streamRef.current?.getTracks().forEach((track) => track.stop()) }, [])
  return <section className="webcam-page"><SectionHead eyebrow="LOCAL VIDEO INPUT" title="Live laptop camera" action={<StatusDot status={status === 'LIVE' || status === 'RECORDING' ? 'live' : status.toLowerCase()} />} /><div className="webcam-layout"><div className="webcam-preview"><video ref={videoRef} muted playsInline /><div className="video-label"><StatusDot status={status === 'LIVE' || status === 'RECORDING' ? 'live' : status.toLowerCase()} /> {status}</div></div><div className="webcam-controls"><label>SELECT CAMERA SOURCE<select value={deviceId} onChange={(event) => setDeviceId(event.target.value)}><option value="">Default laptop webcam</option>{devices.map((device, index) => <option key={device.deviceId} value={device.deviceId}>{device.label || `Camera ${index + 1}`}</option>)}</select></label><div className="control-grid"><button className="primary" onClick={start}>Start camera</button><button onClick={stop}>Stop camera</button><button onClick={capture}>Capture photo</button><button onClick={status === 'RECORDING' ? stopRecording : record}>{status === 'RECORDING' ? 'Stop recording' : 'Start recording'}</button><button onClick={() => videoRef.current?.requestFullscreen?.()}>Fullscreen</button></div>{error && <div className="camera-error">{error}</div>}{captureUrl && <div className="capture-result"><img src={captureUrl} alt="Captured camera frame" /><a className="primary" href={captureUrl} download="attendance-capture.jpg">Download capture</a></div>}<p className="muted-note">AI identification is disabled until a real model is configured. Captured photos are not submitted automatically.</p></div></div></section>
}

void WebcamPage

export default App
