// 指尖打卡工作台
// 负责调用现有 API、渲染今日考勤状态和维护页面交互
(() => {
  'use strict';

  // 页面共享状态
  const state = {
    employees: [],
    summaries: new Map(),
    leaves: [],
    overtimes: [],
    keyword: '',
    department: '',
    leaveStatus: '',
    overtimeStatus: '',
    checkinType: 'in',
    checkinEmployeeId: null,
    deleteEmployeeId: null,
    loading: false,
  };

  const statusLabels = {
    missing: '未签到',
    online: '在岗中',
    done: '已签出',
    quit: '已离职',
  };

  // 请假和加班共用的审批状态说明
  const applicationStatusLabels = {
    pending: '待审批',
    approved: '已通过',
    rejected: '已驳回',
  };

  // 本课程不实现真实登录，审批人使用固定名称演示主管视角
  const DEFAULT_APPROVER = '人事主管';

  // 常用 DOM 查询
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  function iconMarkup(name) {
    return `<svg class="icon" aria-hidden="true"><use href="#icon-${name}"></use></svg>`;
  }

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  function pad(value) {
    return String(value).padStart(2, '0');
  }

  function todayKey(date = new Date()) {
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
  }

  function formatDateCn(date = new Date()) {
    return new Intl.DateTimeFormat('zh-CN', {
      month: 'long',
      day: 'numeric',
      weekday: 'long',
    }).format(date);
  }

  function formatFullDateCn(date = new Date()) {
    return new Intl.DateTimeFormat('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      weekday: 'short',
    }).format(date);
  }

  function formatClock(date = new Date()) {
    return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
  }

  function formatCheckTime(value) {
    if (!value) {
      return '--:--';
    }
    const parts = String(value).split(' ');
    return parts.length > 1 ? parts[1].slice(0, 5) : value;
  }

  function avatarHue(name) {
    return Array.from(String(name || '员工')).reduce((total, char) => {
      return (total + char.codePointAt(0)) % 360;
    }, 0);
  }

  // 统一解析后端响应，错误信息直接交给页面提示
  async function request(path, options = {}) {
    const response = await fetch(path, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    });
    let payload = null;
    try {
      payload = await response.json();
    } catch (error) {
      throw new Error('服务返回了无法解析的数据');
    }
    if (!response.ok || !payload || payload.code !== 200) {
      throw new Error(payload?.message || `请求失败（${response.status}）`);
    }
    return payload.data;
  }

  function showToast(message, type = 'success') {
    const stack = $('#toastStack');
    const toast = document.createElement('div');
    toast.className = `toast ${type === 'error' ? 'error' : ''}`;
    const iconName = type === 'error' ? 'close' : 'check';
    toast.innerHTML = `
      <span class="toast-icon">${iconMarkup(iconName)}</span>
      <p></p>
    `;
    $('p', toast).textContent = message;
    stack.appendChild(toast);
    window.setTimeout(() => {
      toast.classList.add('leaving');
      window.setTimeout(() => toast.remove(), 220);
    }, 3200);
  }

  function getSummary(employeeId) {
    return state.summaries.get(Number(employeeId)) || {
      first_in: null,
      last_out: null,
      records: [],
    };
  }

  function getStatus(employeeId) {
    const employee = employeeById(employeeId);
    if (employee && employee.status !== 'active') {
      return 'quit';
    }
    const summary = getSummary(employeeId);
    if (summary.first_in && summary.last_out) {
      return 'done';
    }
    if (summary.first_in) {
      return 'online';
    }
    return 'missing';
  }

  function getSelectedDepartmentOptions() {
    return Array.from(new Set(state.employees.map((employee) => employee.department)))
      .filter(Boolean)
      .sort((left, right) => left.localeCompare(right, 'zh-CN'));
  }

  function setText(selector, value) {
    const element = $(selector);
    if (element) {
      element.textContent = value;
    }
  }

  function setProgress(selector, value, total) {
    const percent = total > 0 ? Math.round((value / total) * 100) : 0;
    const element = $(selector);
    if (element) {
      element.style.width = `${Math.min(100, percent)}%`;
    }
  }

  function setDates() {
    const now = new Date();
    setText('#headerDate', formatFullDateCn(now));
    setText('#heroDate', formatDateCn(now));
  }

  function startClock() {
    const update = () => setText('#liveClock', formatClock());
    update();
    window.setInterval(update, 1000);
  }

  function renderStats() {
    const activeEmployees = state.employees.filter((employee) => employee.status === 'active');
    const total = activeEmployees.length;
    const checkedIn = activeEmployees.filter((employee) => getSummary(employee.id).first_in).length;
    const onDuty = activeEmployees.filter((employee) => {
      const summary = getSummary(employee.id);
      return summary.first_in && !summary.last_out;
    }).length;
    const completed = activeEmployees.filter((employee) => {
      const summary = getSummary(employee.id);
      return summary.first_in && summary.last_out;
    }).length;
    const missing = Math.max(0, total - checkedIn);
    const rate = total > 0 ? Math.round((checkedIn / total) * 100) : 0;

    setText('#statTotal', total);
    setText('#statCheckedIn', checkedIn);
    setText('#statOnDuty', onDuty);
    setText('#statCompleted', completed);
    setText('#heroOnDuty', onDuty);
    setText('#heroMissing', missing);
    setText('#attendanceRate', `${rate}%`);
    setProgress('#statTotalBar', total, total);
    setProgress('#statCheckedInBar', checkedIn, total);
    setProgress('#statOnDutyBar', onDuty, total);
    setProgress('#statCompletedBar', completed, total);

    const ring = $('#attendanceRing');
    if (ring) {
      ring.style.setProperty('--rate', `${rate}%`);
    }

    const footnote = total > 0
      ? `已有 ${checkedIn} / ${total} 位员工完成签到`
      : '添加员工后，今日考勤会实时汇总到这里';
    setText('#heroFootnote', footnote);

    const heroAvatars = $('#heroAvatars');
    heroAvatars.innerHTML = state.employees.slice(0, 4).map((employee) => {
      return `<span class="mini-avatar" style="--avatar-hue: ${avatarHue(employee.name)}">
        ${escapeHtml(Array.from(employee.name)[0] || '员')}
      </span>`;
    }).join('');

    let hint = '还没有员工档案，先添加第一位团队成员。';
    if (total > 0 && missing > 0) {
      hint = `还有 ${missing} 位员工未签到，记得提醒一下。`;
    } else if (total > 0 && onDuty > 0) {
      hint = `${onDuty} 位员工正在岗，今日签到率 ${rate}%。`;
    } else if (total > 0) {
      hint = '今日全员已完成签出，收工。';
    }
    setText('#sidebarHint', hint);
  }

  function renderDepartmentOptions() {
    const departments = getSelectedDepartmentOptions();
    const filter = $('#departmentFilter');
    const current = state.department;
    filter.innerHTML = '<option value="">全部部门</option>';
    departments.forEach((department) => {
      const option = document.createElement('option');
      option.value = department;
      option.textContent = department;
      filter.appendChild(option);
    });
    if (departments.includes(current)) {
      filter.value = current;
    } else {
      state.department = '';
      filter.value = '';
    }

    const dataList = $('#departmentOptions');
    dataList.innerHTML = '';
    departments.forEach((department) => {
      const option = document.createElement('option');
      option.value = department;
      dataList.appendChild(option);
    });
  }

  function filteredEmployees() {
    const keyword = state.keyword.trim().toLowerCase();
    return state.employees.filter((employee) => {
      const matchesKeyword = !keyword
        || employee.name.toLowerCase().includes(keyword)
        || employee.employee_no.toLowerCase().includes(keyword);
      const matchesDepartment = !state.department || employee.department === state.department;
      return matchesKeyword && matchesDepartment;
    });
  }

  function actionMarkup(employee) {
    const status = getStatus(employee.id);
    let checkButton = '';
    if (status === 'quit') {
      checkButton = '<span class="row-action" aria-disabled="true">已离职</span>';
    } else if (status === 'missing') {
      checkButton = `
        <button class="row-action primary" type="button" data-action="checkin" data-id="${employee.id}">
          ${iconMarkup('check')} 签到
        </button>
      `;
    } else if (status === 'online') {
      checkButton = `
        <button class="row-action primary" type="button" data-action="checkout" data-id="${employee.id}">
          ${iconMarkup('arrow')} 签出
        </button>
      `;
    } else {
      checkButton = '<span class="row-action" aria-disabled="true">已完成</span>';
    }
    return `
      ${checkButton}
      <button class="row-action icon-only" type="button" data-action="edit" data-id="${employee.id}"
        title="编辑员工" aria-label="编辑员工">${iconMarkup('edit')}</button>
      <button class="row-action icon-only danger" type="button" data-action="delete" data-id="${employee.id}"
        title="员工离职" aria-label="员工离职">${iconMarkup('trash')}</button>
    `;
  }

  function renderEmployees() {
    const body = $('#employeeTableBody');
    const items = filteredEmployees();
    if (items.length === 0) {
      const hasEmployees = state.employees.length > 0;
      const emptyMessage = hasEmployees
        ? '没有匹配的员工，换个关键词试试。'
        : '还没有员工档案，先添加第一位员工。';
      const createButton = hasEmployees
        ? ''
        : '<br><button class="soft-button" data-action="create" type="button">员工入职</button>';
      body.innerHTML = `
        <tr class="empty-row">
          <td colspan="6">
            ${emptyMessage}
            ${createButton}
          </td>
        </tr>
      `;
    } else {
      body.innerHTML = items.map((employee) => {
        const summary = getSummary(employee.id);
        const status = getStatus(employee.id);
        const firstIn = formatCheckTime(summary.first_in);
        const lastOut = formatCheckTime(summary.last_out);
        const avatar = Array.from(employee.name)[0] || '员';
        return `
          <tr>
            <td>
              <div class="employee-cell">
                <span class="employee-avatar" style="--avatar-hue: ${avatarHue(employee.name)}">
                  ${escapeHtml(avatar)}
                </span>
                <div class="employee-meta">
                  <strong>${escapeHtml(employee.name)}</strong>
                  <span>${escapeHtml(employee.employee_no)}</span>
                </div>
              </div>
            </td>
            <td data-label="部门"><span class="department-pill">${escapeHtml(employee.department)}</span></td>
            <td data-label="签到"><span class="time-text ${summary.first_in ? '' : 'muted'}">${firstIn}</span></td>
            <td data-label="签出"><span class="time-text ${summary.last_out ? '' : 'muted'}">${lastOut}</span></td>
            <td data-label="状态"><span class="status-pill ${status}">${statusLabels[status]}</span></td>
            <td class="action-cell" data-label="操作">
              <div class="row-actions">${actionMarkup(employee)}</div>
            </td>
          </tr>
        `;
      }).join('');
    }

    const summaryText = items.length === state.employees.length
      ? `共 ${state.employees.length} 位员工`
      : `筛选出 ${items.length} 位 · 共 ${state.employees.length} 位员工`;
    setText('#tableSummary', summaryText);
  }

  function renderActivity() {
    const records = [];
    state.employees.forEach((employee) => {
      getSummary(employee.id).records.forEach((record) => {
        records.push({ ...record, employee });
      });
    });
    records.sort((left, right) => String(right.check_time).localeCompare(String(left.check_time)));

    setText('#activityCount', `${records.length} 条`);
    setText('#navActivityCount', records.length);
    const list = $('#activityList');
    if (records.length === 0) {
      list.innerHTML = `
        <div class="empty-compact">
          <span class="empty-ring">${iconMarkup('clock')}</span>
          <p>今日还没有打卡记录</p>
          <span>完成第一次签到后会显示在这里</span>
        </div>
      `;
      return;
    }

    list.innerHTML = records.slice(0, 20).map((record) => {
      const isIn = record.check_type === 'in';
      const action = isIn ? '完成签到' : '完成签出';
      return `
        <div class="activity-item">
          <span class="activity-icon ${isIn ? '' : 'out'}">
            ${iconMarkup(isIn ? 'check' : 'arrow')}
          </span>
          <div class="activity-copy">
            <strong>${escapeHtml(record.employee.name)}</strong>
            <span>${escapeHtml(record.employee.department)} · ${action}</span>
          </div>
          <time class="activity-time">${formatCheckTime(record.check_time)}</time>
        </div>
      `;
    }).join('');
  }

  function renderAll() {
    renderStats();
    renderDepartmentOptions();
    renderEmployees();
    renderActivity();
    renderLeaves();
    renderOvertimes();
  }

  // 找到员工对象，申请列表需要展示员工姓名
  function employeeById(employeeId) {
    return state.employees.find((item) => Number(item.id) === Number(employeeId));
  }

  // 申请列表中的员工单元格
  function employeeCell(employeeId) {
    const employee = employeeById(employeeId);
    if (!employee) {
      return '<span class="muted">未知员工</span>';
    }
    const avatar = Array.from(employee.name)[0] || '员';
    return `
      <div class="employee-cell">
        <span class="employee-avatar" style="--avatar-hue: ${avatarHue(employee.name)}">
          ${escapeHtml(avatar)}
        </span>
        <div class="employee-meta">
          <strong>${escapeHtml(employee.name)}</strong>
          <span>${escapeHtml(employee.department)}</span>
        </div>
      </div>
    `;
  }

  // 只有待审批的申请才展示审批按钮
  function reviewActions(type, item) {
    if (item.status !== 'pending') {
      return `<span class="muted">${applicationStatusLabels[item.status] || item.status}</span>`;
    }
    return `
      <div class="row-actions">
        <button class="row-action primary" type="button"
          data-review-type="${type}" data-review-action="approve" data-id="${item.id}">通过</button>
        <button class="row-action icon-only danger" type="button"
          data-review-type="${type}" data-review-action="reject" data-id="${item.id}"
          title="驳回" aria-label="驳回">${iconMarkup('close')}</button>
      </div>
    `;
  }

  function renderLeaves() {
    const body = $('#leaveTableBody');
    if (!body) {
      return;
    }
    if (state.leaves.length === 0) {
      body.innerHTML = `
        <tr class="empty-row">
          <td colspan="6">还没有请假申请，提交第一条申请试试。</td>
        </tr>
      `;
    } else {
      body.innerHTML = state.leaves.map((item) => `
        <tr>
          <td>${employeeCell(item.employee_id)}</td>
          <td data-label="类型"><span class="department-pill">${escapeHtml(item.leave_type)}</span></td>
          <td data-label="日期区间">
            <span class="time-text">${escapeHtml(item.start_date)} ~ ${escapeHtml(item.end_date)}</span>
          </td>
          <td data-label="天数">${item.days} 天</td>
          <td data-label="状态">
            <span class="status-pill ${item.status}">${applicationStatusLabels[item.status]}</span>
          </td>
          <td class="action-cell" data-label="操作">${reviewActions('leave', item)}</td>
        </tr>
      `).join('');
    }
    const pending = state.leaves.filter((item) => item.status === 'pending').length;
    setText('#navLeaveCount', pending);
    setText('#leaveSummary', `共 ${state.leaves.length} 条请假申请 · ${pending} 条待审批`);
  }

  function renderOvertimes() {
    const body = $('#overtimeTableBody');
    if (!body) {
      return;
    }
    if (state.overtimes.length === 0) {
      body.innerHTML = `
        <tr class="empty-row">
          <td colspan="6">还没有加班申请，提交第一条申请试试。</td>
        </tr>
      `;
    } else {
      body.innerHTML = state.overtimes.map((item) => `
        <tr>
          <td>${employeeCell(item.employee_id)}</td>
          <td data-label="加班日期"><span class="time-text">${escapeHtml(item.work_date)}</span></td>
          <td data-label="时长">${item.hours} 小时</td>
          <td data-label="原因"><span class="muted">${escapeHtml(item.reason || '--')}</span></td>
          <td data-label="状态">
            <span class="status-pill ${item.status}">${applicationStatusLabels[item.status]}</span>
          </td>
          <td class="action-cell" data-label="操作">${reviewActions('overtime', item)}</td>
        </tr>
      `).join('');
    }
    const pending = state.overtimes.filter((item) => item.status === 'pending').length;
    setText('#navOvertimeCount', pending);
    setText('#overtimeSummary', `共 ${state.overtimes.length} 条加班申请 · ${pending} 条待审批`);
  }

  // 拉取请假和加班列表
  async function loadApplications() {
    const leaveQuery = state.leaveStatus ? `?status=${state.leaveStatus}` : '';
    const overtimeQuery = state.overtimeStatus ? `?status=${state.overtimeStatus}` : '';
    const [leaveData, overtimeData] = await Promise.all([
      request(`/api/leaves${leaveQuery}`),
      request(`/api/overtimes${overtimeQuery}`),
    ]);
    state.leaves = leaveData.items || [];
    state.overtimes = overtimeData.items || [];
  }

  // 刷新申请数据并重绘列表
  async function refreshApplications() {
    try {
      await loadApplications();
      renderLeaves();
      renderOvertimes();
    } catch (error) {
      showToast(`申请数据载入失败：${error.message}`, 'error');
    }
  }

  // 申请弹窗只列出在职员工，离职员工不能提交申请
  function populateApplicationEmployees(select) {
    const activeEmployees = state.employees.filter((employee) => employee.status === 'active');
    select.replaceChildren();
    if (activeEmployees.length === 0) {
      const option = document.createElement('option');
      option.value = '';
      option.textContent = '暂无在职员工';
      select.appendChild(option);
      select.disabled = true;
      return;
    }
    select.disabled = false;
    activeEmployees.forEach((employee) => {
      const option = document.createElement('option');
      option.value = employee.id;
      option.textContent = `${employee.name}（${employee.department}）`;
      select.appendChild(option);
    });
  }

  // 计算请假天数，包含首尾两天
  function updateLeaveDays() {
    const startDate = $('#leaveStartDate').value;
    const endDate = $('#leaveEndDate').value;
    if (!startDate || !endDate) {
      $('#leaveDays').value = '自动计算';
      return;
    }
    const start = new Date(`${startDate}T00:00:00`);
    const end = new Date(`${endDate}T00:00:00`);
    const days = Math.round((end - start) / 86400000) + 1;
    $('#leaveDays').value = days > 0 ? `${days} 天` : '开始日期不能晚于结束日期';
  }

  function openLeaveModal() {
    const form = $('#leaveForm');
    form.reset();
    populateApplicationEmployees($('#leaveEmployee'));
    $('#leaveStartDate').value = todayKey();
    $('#leaveEndDate').value = todayKey();
    updateLeaveDays();
    openModal('leaveModal');
  }

  function openOvertimeModal() {
    const form = $('#overtimeForm');
    form.reset();
    populateApplicationEmployees($('#overtimeEmployee'));
    $('#overtimeDate').value = todayKey();
    $('#overtimeHours').value = '2';
    openModal('overtimeModal');
  }

  async function submitLeave(event) {
    event.preventDefault();
    const employeeId = Number($('#leaveEmployee').value);
    const startDate = $('#leaveStartDate').value;
    const endDate = $('#leaveEndDate').value;
    const reason = $('#leaveReason').value.trim();
    if (!employeeId) {
      showToast('请选择请假员工', 'error');
      return;
    }
    if (!startDate || !endDate) {
      showToast('请选择开始和结束日期', 'error');
      return;
    }

    const button = $('#leaveSubmitButton');
    button.disabled = true;
    try {
      await request('/api/leaves', {
        method: 'POST',
        body: JSON.stringify({
          employee_id: employeeId,
          leave_type: $('#leaveType').value,
          start_date: startDate,
          end_date: endDate,
          reason,
        }),
      });
      closeModal('leaveModal');
      showToast('请假申请已提交，等待主管审批');
      await refreshApplications();
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      button.disabled = false;
    }
  }

  async function submitOvertime(event) {
    event.preventDefault();
    const employeeId = Number($('#overtimeEmployee').value);
    const workDate = $('#overtimeDate').value;
    const hours = Number($('#overtimeHours').value);
    const reason = $('#overtimeReason').value.trim();
    if (!employeeId) {
      showToast('请选择加班员工', 'error');
      return;
    }
    if (!workDate) {
      showToast('请选择加班日期', 'error');
      return;
    }
    if (!hours || hours <= 0 || hours > 24) {
      showToast('加班时长必须大于 0 且不超过 24 小时', 'error');
      return;
    }

    const button = $('#overtimeSubmitButton');
    button.disabled = true;
    try {
      await request('/api/overtimes', {
        method: 'POST',
        body: JSON.stringify({
          employee_id: employeeId,
          work_date: workDate,
          hours,
          reason,
        }),
      });
      closeModal('overtimeModal');
      showToast('加班申请已提交，等待主管审批');
      await refreshApplications();
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      button.disabled = false;
    }
  }

  // 审批通过或驳回申请
  async function reviewApplication(type, id, action) {
    const resource = type === 'leave' ? 'leaves' : 'overtimes';
    try {
      await request(`/api/${resource}/${id}/${action}`, {
        method: 'POST',
        body: JSON.stringify({ approver: DEFAULT_APPROVER }),
      });
      showToast(action === 'approve' ? '申请已通过' : '申请已驳回');
      await refreshApplications();
    } catch (error) {
      showToast(error.message, 'error');
    }
  }

  function renderLoading() {
    $('#employeeTableBody').innerHTML = `
      <tr class="loading-row">
        <td colspan="6"><span class="loader"></span> 正在载入员工数据…</td>
      </tr>
    `;
  }

  async function loadDashboard(showRefreshToast = false) {
    if (state.loading) {
      return;
    }
    state.loading = true;
    const refreshButton = $('#refreshButton');
    refreshButton.disabled = true;
    renderLoading();
    try {
      const data = await request('/api/employees');
      state.employees = data.items || [];
      const workDate = todayKey();
      const entries = await Promise.all(state.employees.map(async (employee) => {
        try {
          const summary = await request(
            `/api/checkins?employee_id=${employee.id}&date=${workDate}`,
          );
          return [Number(employee.id), summary];
        } catch (error) {
          return [Number(employee.id), { first_in: null, last_out: null, records: [] }];
        }
      }));
      state.summaries = new Map(entries);
      renderAll();
      await refreshApplications();
      if (showRefreshToast) {
        showToast('考勤数据已刷新');
      }
    } catch (error) {
      $('#employeeTableBody').innerHTML = `
        <tr class="empty-row">
          <td colspan="6">数据载入失败：${escapeHtml(error.message)}</td>
        </tr>
      `;
      showToast(error.message, 'error');
    } finally {
      state.loading = false;
      refreshButton.disabled = false;
    }
  }

  function openModal(modalId) {
    const modal = $(`#${modalId}`);
    if (!modal) {
      return;
    }
    modal.hidden = false;
    document.body.style.overflow = 'hidden';
    window.setTimeout(() => {
      const focusTarget = $('input:not([type="hidden"]), select, button', modal);
      focusTarget?.focus();
    }, 60);
  }

  function closeModal(modalId) {
    const modal = $(`#${modalId}`);
    if (!modal) {
      return;
    }
    modal.hidden = true;
    if ($$('.modal-layer:not([hidden])').length === 0) {
      document.body.style.overflow = '';
    }
  }

  function closeAllModals() {
    $$('.modal-layer').forEach((modal) => {
      modal.hidden = true;
    });
    document.body.style.overflow = '';
  }

  function openEmployeeForm(employee = null) {
    const form = $('#employeeForm');
    form.reset();
    $('#employeeId').value = employee ? employee.id : '';
    $('#employeeName').value = employee ? employee.name : '';
    $('#employeeNo').value = employee ? employee.employee_no : '';
    $('#employeeDepartment').value = employee ? employee.department : '';
    setText('#employeeModalTitle', employee ? '编辑员工' : '新增员工');
    setText('#employeeSubmitButton', employee ? '保存修改' : '保存员工');
    openModal('employeeModal');
  }

  async function saveEmployee(event) {
    event.preventDefault();
    const employeeId = $('#employeeId').value;
    const name = $('#employeeName').value.trim();
    const employeeNo = $('#employeeNo').value.trim();
    const department = $('#employeeDepartment').value.trim();
    if (!name || !employeeNo || !department) {
      showToast('姓名、工号和部门都不能为空', 'error');
      return;
    }

    const button = $('#employeeSubmitButton');
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = '保存中…';
    try {
      await request(employeeId ? `/api/employees/${employeeId}` : '/api/employees', {
        method: employeeId ? 'PUT' : 'POST',
        body: JSON.stringify({ name, employee_no: employeeNo, department }),
      });
      closeModal('employeeModal');
      showToast(employeeId ? '员工信息已更新' : '员工已成功入职');
      await loadDashboard();
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      button.disabled = false;
      button.textContent = originalText;
    }
  }

  function eligibleEmployees(type) {
    return state.employees.filter((employee) => {
      if (employee.status !== 'active') {
        return false;
      }
      const summary = getSummary(employee.id);
      return type === 'in' ? !summary.first_in : summary.first_in && !summary.last_out;
    });
  }

  function setCheckinType(type) {
    state.checkinType = type;
    $$('.segment-button').forEach((button) => {
      button.classList.toggle('active', button.dataset.checkinType === type);
    });
    setText('#checkinModalTitle', type === 'in' ? '上班签到' : '下班签出');
    setText('#checkinSubmitButton', type === 'in' ? '确认签到' : '确认签出');
    populateCheckinEmployees();
  }

  function populateCheckinEmployees(preferredId = null) {
    const select = $('#checkinEmployee');
    const submit = $('#checkinSubmitButton');
    const employees = eligibleEmployees(state.checkinType);
    select.replaceChildren();

    if (employees.length === 0) {
      const option = document.createElement('option');
      option.value = '';
      option.textContent = state.checkinType === 'in' ? '所有员工都已签到' : '当前没有可签出的员工';
      select.appendChild(option);
      select.disabled = true;
      submit.disabled = true;
      state.checkinEmployeeId = null;
      setText('#checkinHint', '当前没有符合条件的人员，请先检查员工状态。');
      return;
    }

    employees.forEach((employee) => {
      const summary = getSummary(employee.id);
      const suffix = state.checkinType === 'in'
        ? '未签到'
        : `已签到 ${formatCheckTime(summary.first_in)}`;
      const option = document.createElement('option');
      option.value = employee.id;
      option.textContent = `${employee.name} · ${employee.department} · ${suffix}`;
      select.appendChild(option);
    });
    select.disabled = false;
    submit.disabled = false;

    const targetId = preferredId || state.checkinEmployeeId;
    const hasTarget = employees.some((employee) => Number(employee.id) === Number(targetId));
    const selected = hasTarget ? Number(targetId) : Number(employees[0].id);
    select.value = String(selected);
    state.checkinEmployeeId = selected;
    updateCheckinHint();
  }

  function updateCheckinHint() {
    const employee = state.employees.find((item) => {
      return Number(item.id) === Number(state.checkinEmployeeId);
    });
    if (!employee) {
      setText('#checkinHint', '请选择员工后确认打卡。');
      return;
    }
    const summary = getSummary(employee.id);
    if (state.checkinType === 'in') {
      setText('#checkinHint', `将为 ${employee.name} 记录今天的上班签到时间。`);
    } else {
      const checkinTime = formatCheckTime(summary.first_in);
      setText('#checkinHint', `${employee.name} 今天 ${checkinTime} 已签到，现在记录签出。`);
    }
  }

  function openCheckinModal(type, employeeId = null) {
    state.checkinEmployeeId = employeeId ? Number(employeeId) : null;
    setCheckinType(type);
    populateCheckinEmployees(employeeId ? Number(employeeId) : null);
    openModal('checkinModal');
  }

  async function submitCheckin() {
    const employeeId = Number($('#checkinEmployee').value);
    if (!employeeId) {
      showToast('请选择需要打卡的员工', 'error');
      return;
    }
    const button = $('#checkinSubmitButton');
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = '记录中…';
    try {
      await request(`/api/checkins/${state.checkinType}`, {
        method: 'POST',
        body: JSON.stringify({ employee_id: employeeId }),
      });
      closeModal('checkinModal');
      showToast(state.checkinType === 'in' ? '签到成功，状态已更新' : '签出成功，辛苦了');
      await loadDashboard();
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      button.disabled = false;
      button.textContent = originalText;
    }
  }

  function openDeleteModal(employeeId) {
    const employee = state.employees.find((item) => Number(item.id) === Number(employeeId));
    if (!employee) {
      return;
    }
    state.deleteEmployeeId = Number(employeeId);
    setText('#deleteEmployeeName', `${employee.name}（${employee.employee_no}）`);
    openModal('deleteModal');
  }

  async function deleteEmployee() {
    if (!state.deleteEmployeeId) {
      return;
    }
    const button = $('#deleteSubmitButton');
    button.disabled = true;
    button.textContent = '删除中…';
    try {
      await request(`/api/employees/${state.deleteEmployeeId}`, { method: 'DELETE' });
      closeModal('deleteModal');
      showToast('员工已离职，历史考勤记录保留');
      state.deleteEmployeeId = null;
      await loadDashboard();
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      button.disabled = false;
      button.textContent = '确认离职';
    }
  }

  function toggleSidebar(forceOpen = null) {
    const sidebar = $('#sidebar');
    const backdrop = $('#mobileBackdrop');
    const shouldOpen = forceOpen === null ? !sidebar.classList.contains('open') : forceOpen;
    sidebar.classList.toggle('open', shouldOpen);
    backdrop.hidden = !shouldOpen;
  }

  function bindEvents() {
    $('#menuButton').addEventListener('click', () => toggleSidebar());
    $('#mobileBackdrop').addEventListener('click', () => toggleSidebar(false));
    $('#openEmployeeModal').addEventListener('click', () => openEmployeeForm());
    $('#refreshButton').addEventListener('click', () => loadDashboard(true));
    $('#employeeForm').addEventListener('submit', saveEmployee);
    $('#checkinSubmitButton').addEventListener('click', submitCheckin);
    $('#deleteSubmitButton').addEventListener('click', deleteEmployee);
    $('#openLeaveModal').addEventListener('click', openLeaveModal);
    $('#leaveForm').addEventListener('submit', submitLeave);
    $('#openOvertimeModal').addEventListener('click', openOvertimeModal);
    $('#overtimeForm').addEventListener('submit', submitOvertime);

    $('#leaveStartDate').addEventListener('change', updateLeaveDays);
    $('#leaveEndDate').addEventListener('change', updateLeaveDays);

    $('#leaveStatusFilter').addEventListener('change', (event) => {
      state.leaveStatus = event.target.value;
      refreshApplications();
    });

    $('#overtimeStatusFilter').addEventListener('change', (event) => {
      state.overtimeStatus = event.target.value;
      refreshApplications();
    });

    ['#leaveTableBody', '#overtimeTableBody'].forEach((selector) => {
      $(selector).addEventListener('click', (event) => {
        const button = event.target.closest('[data-review-action]');
        if (!button) {
          return;
        }
        reviewApplication(button.dataset.reviewType, button.dataset.id, button.dataset.reviewAction);
      });
    });

    $('#searchInput').addEventListener('input', (event) => {
      state.keyword = event.target.value;
      renderEmployees();
    });

    $('#departmentFilter').addEventListener('change', (event) => {
      state.department = event.target.value;
      renderEmployees();
    });

    $$('[data-quick-checkin]').forEach((button) => {
      button.addEventListener('click', () => openCheckinModal(button.dataset.quickCheckin));
    });

    $$('.segment-button').forEach((button) => {
      button.addEventListener('click', () => {
        state.checkinEmployeeId = null;
        setCheckinType(button.dataset.checkinType);
      });
    });

    $('#checkinEmployee').addEventListener('change', (event) => {
      state.checkinEmployeeId = Number(event.target.value) || null;
      updateCheckinHint();
    });

    $('#employeeTableBody').addEventListener('click', (event) => {
      const button = event.target.closest('[data-action]');
      if (!button) {
        return;
      }
      const employeeId = Number(button.dataset.id);
      if (button.dataset.action === 'checkin') {
        openCheckinModal('in', employeeId);
      } else if (button.dataset.action === 'checkout') {
        openCheckinModal('out', employeeId);
      } else if (button.dataset.action === 'edit') {
        const employee = state.employees.find((item) => Number(item.id) === employeeId);
        openEmployeeForm(employee);
      } else if (button.dataset.action === 'delete') {
        openDeleteModal(employeeId);
      } else if (button.dataset.action === 'create') {
        openEmployeeForm();
      }
    });

    $$('[data-close-modal]').forEach((button) => {
      button.addEventListener('click', () => closeModal(button.dataset.closeModal));
    });

    $$('.modal-layer').forEach((modal) => {
      modal.addEventListener('click', (event) => {
        if (event.target === modal) {
          closeModal(modal.id);
        }
      });
    });

    $$('.nav-link').forEach((link) => {
      link.addEventListener('click', () => {
        $$('.nav-link').forEach((item) => item.classList.remove('active'));
        link.classList.add('active');
        if (window.innerWidth <= 1020) {
          toggleSidebar(false);
        }
      });
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        closeAllModals();
        toggleSidebar(false);
      }
    });
  }

  function init() {
    setDates();
    startClock();
    bindEvents();
    loadDashboard();
  }

  document.addEventListener('DOMContentLoaded', init);
})();
