const $ = id => document.getElementById(id);
let samples = [], selected = null, uploaded = null, objectUrl = null, localPath = null;
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function resetResults() {
  document.querySelectorAll('audio').forEach(a => a.pause());
  $('results').replaceChildren();
  $('result-count').textContent = '';
  $('error').hidden = true;
  $('intermediate').hidden = true;
  $('status').textContent = 'Sẵn sàng. Bấm “Tìm 5 âm tương đồng” để so sánh.';
}
function clearObjectUrl() {
  if (objectUrl) URL.revokeObjectURL(objectUrl);
  objectUrl = null;
}
function chooseSample() {
  resetResults();
  clearObjectUrl();
  uploaded = null;
  localPath = null;
  $('upload').value = '';
  selected = samples.find(s => s.id === Number($('sample').value));
  $('query-name').textContent = selected.name;
  $('query-meta').textContent = `${selected.label} · ${selected.duration.toFixed(2)} giây · Trong kho`;
  $('query-audio').src = `/audio/${selected.id}`;
}
function populate() {
  const list = samples.filter(s => !$('label-filter').value || s.label === $('label-filter').value);
  $('sample').replaceChildren(...list.map(s => {
    const option = element('option', `${s.label} · ${s.name}`);
    option.value = s.id;
    return option;
  }));
  chooseSample();
}
function table(title, head, rows) {
  const wrap = element('div', undefined, 'mid');
  wrap.append(element('h4', title));
  const t = element('table');
  const tr = element('tr');
  head.forEach(h => tr.append(element('th', h)));
  t.append(tr);
  for (const row of rows) {
    const r = element('tr');
    row.forEach(c => r.append(element('td', String(c))));
    t.append(r);
  }
  wrap.append(t);
  return wrap;
}
function showError(message) {
  $('error').textContent = message;
  $('error').hidden = false;
}
async function jsonRequest(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw Error(data.error || 'Không thực hiện được yêu cầu.');
  return data;
}
function render(data) {
  $('results').replaceChildren();
  for (const r of data.ket_qua) {
    const card = element('article', undefined, 'result');
    card.append(element('span', String(r.hang).padStart(2, '0'), 'rank'));
    const body = element('div');
    body.append(element('h3', r.nhan.replaceAll('_', ' ')));
    body.append(element('p', `${r.duong_dan.split('/').pop()} · ${r.nguon} · ${r.thoi_luong_s.toFixed(2)} s`, 'filename'));
    const audio = element('audio');
    audio.controls = true;
    audio.preload = 'metadata';
    audio.src = `/audio/${r.ma_tep}`;
    audio.setAttribute('aria-label', `Nghe kết quả ${r.hang}: ${r.nhan}`);
    body.append(audio);
    const details = element('details');
    details.append(element('summary', 'Đối chiếu đặc trưng âm thanh'));
    details.append(element('p', 'Giống nhất: ' + r.giai_thich.giong.map(x => x[0]).join(', ')));
    details.append(element('p', 'Khác nhất: ' + r.giai_thich.khac.map(x => `${x[0]} (${x[1].toFixed(1)}σ)`).join(', ')));
    body.append(details);
    const score = element('div', r.do_tuong_dong.toFixed(3), 'score');
    score.append(element('small', 'tương đồng'), element('small', `d = ${r.khoang_cach.toFixed(3)}`));
    card.append(body, score);
    $('results').append(card);
  }
  $('result-count').textContent = `${data.ket_qua.length} kết quả · Bộ ${data.bo}`;
  $('status').textContent = data.trung_tep_trong_kho.length
    ? 'Đã loại chính âm thanh truy vấn khỏi kết quả vì có trong kho.'
    : 'Đã tìm xong. Phát âm thanh truy vấn và từng kết quả để đối chiếu.';
  if (data.trung_gian) {
    $('intermediate').hidden = false;
    $('intermediate-values').replaceChildren(
      table('Khoảng cách theo từng bộ (d_C² = ½d_A² + ½d_B²)', ['Hạng', 'Nhạc cụ', 'd_A', 'd_B', 'd_C', 's = 1/(1+d)'],
        data.ket_qua.map(r => [r.hang, r.nhan, r.khoang_cach_theo_bo.A.toFixed(4), r.khoang_cach_theo_bo.B.toFixed(4),
          r.khoang_cach_theo_bo.C.toFixed(4), r.do_tuong_dong.toFixed(4)])),
      table('Kiểm tra tín hiệu (Mục 2)', ['Số đo', 'Giá trị'],
        Object.entries(data.kiem_tra_tin_hieu).map(([k, v]) => [k, v.toFixed(4)])),
      table('60 đặc trưng của truy vấn: z = (x − μ) / s', ['Chiều', 'Thuộc tính', 'x', 'μ', 's', 'z'],
        data.trung_gian.map(d => [d.chieu, d.ten, d.x.toPrecision(5), d.mu.toPrecision(5), d.s.toPrecision(5), d.z.toFixed(3)])));
  }
}
$('label-filter').addEventListener('change', populate);
$('sample').addEventListener('change', chooseSample);
$('random').addEventListener('click', () => {
  const options = [...$('sample').options].filter(o => o.value !== $('sample').value);
  if (options.length) $('sample').value = options[Math.floor(Math.random() * options.length)].value;
  chooseSample();
});
$('feature').addEventListener('change', resetResults);
function chooseUpload(file) {
  if (!file) return;
  resetResults();
  if (file.size > 30 * 1024 * 1024 || !file.size) {
    $('upload').value = '';
    return showError('Chọn tệp có dung lượng từ 1 byte đến 30 MB.');
  }
  clearObjectUrl();
  uploaded = file;
  localPath = null;
  selected = null;
  objectUrl = URL.createObjectURL(file);
  $('query-audio').src = objectUrl;
  $('query-name').textContent = file.name;
  $('query-meta').textContent = `File từ máy · ${(file.size / 1024).toFixed(0)} KB`;
}
$('upload').addEventListener('change', () => chooseUpload($('upload').files[0]));
for (const type of ['dragenter', 'dragover']) $('dropzone').addEventListener(type, event => {
  event.preventDefault(); $('dropzone').classList.add('dragover');
});
$('dropzone').addEventListener('dragleave', () => $('dropzone').classList.remove('dragover'));
$('dropzone').addEventListener('drop', event => {
  event.preventDefault(); $('dropzone').classList.remove('dragover');
  if (!$('controls').disabled) chooseUpload(event.dataTransfer.files[0]);
});
$('local-open').addEventListener('click', () => {
  const path = $('local-path').value.trim();
  if (!path) return showError('Dán đường dẫn file âm thanh trước.');
  localPath = path; uploaded = null; selected = null;
  clearObjectUrl(); $('query-audio').removeAttribute('src');
  $('query-name').textContent = path.split('/').pop();
  $('query-meta').textContent = 'File trên máy · đang đọc';
  $('search').click();
});
$('query-audio').addEventListener('error', () => {
  if (uploaded) $('query-meta').textContent = 'Bấm tìm kiếm để tạo bản nghe WAV nếu trình duyệt không hỗ trợ định dạng này.';
});
$('search').addEventListener('click', async () => {
  resetResults();
  $('controls').disabled = true;
  $('search').textContent = 'Đang tìm kiếm…';
  $('status').textContent = 'Đang phân tích âm thanh và so sánh với kho…';
  try {
    const bo = $('feature').value;
    const data = localPath
      ? await jsonRequest(`/api/local?bo=${bo}`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:localPath})})
      : uploaded
      ? await jsonRequest(`/api/upload?bo=${bo}`, {method: 'POST', body: uploaded})
      : await jsonRequest(`/api/search?id=${selected.id}&bo=${bo}`);
    if (data.preview) {
      clearObjectUrl();
      $('query-audio').src = data.preview;
      $('query-meta').textContent = `File từ máy · ${data.thoi_luong_s.toFixed(2)} giây`;
      if (data.filename) $('query-name').textContent = data.filename;
    }
    render(data);
  } catch (error) {
    showError(error.message);
    $('status').textContent = 'Chưa tìm được kết quả. Kiểm tra tệp rồi thử lại.';
  } finally {
    $('controls').disabled = false;
    $('search').textContent = 'Tìm 5 âm tương đồng';
  }
});
// Only one player sounds at a time, making A/B listening easier.
document.addEventListener('play', event => {
  if (event.target.tagName === 'AUDIO') {
    document.querySelectorAll('audio').forEach(a => { if (a !== event.target) a.pause(); });
  }
}, true);
async function init() {
  try {
    samples = await jsonRequest('/api/samples');
    const labels = [...new Set(samples.map(s => s.label))].sort();
    for (const label of labels) {
      const option = element('option', label.replaceAll('_', ' '));
      option.value = label;
      $('label-filter').append(option);
    }
    $('inventory').textContent = `${samples.length} âm thanh · ${labels.length} nhạc cụ`;
    populate();
    $('controls').disabled = false;
  } catch (error) { showError('Không nạp được kho âm thanh: ' + error.message); }
}
init();
