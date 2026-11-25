## Google образца конца 2011 года поверх настоящего Google: когда в браузере компа открывается главная Google
## или страница поиска, в неё подставляется старая вёрстка (чёрная полоса сверху, логотип 2011, серые кнопки,
## синие заголовки, зелёный адрес, «Goooooogle» внизу). Результаты берутся из настоящей выдачи, так что
## поиск живой. Если Google поменял вёрстку и результатов не нашлось — страница остаётся как есть.
## Картинки — настоящие из 2011 (web.archive.org): assets/pc/google2011/.
class_name Google2011

const LOGO := "res://assets/pc/google2011/ps_logo2.png"
const NAV := "res://assets/pc/google2011/nav_logo99.png"

static var _js := ""


## Это главная Google или страница обычного поиска (не картинки, не карты)?
static func is_google(url: String) -> bool:
	var rest := url.get_slice("://", 1)
	var host := rest.get_slice("/", 0)
	var path := "/" + rest.get_slice("/", 1).get_slice("?", 0).get_slice("#", 0)
	if not (host == "google.com" or host.begins_with("www.google.")):
		return false
	return path in ["/", "/webhp", "/search"] and not url.contains("tbm=") and not url.contains("udm=")


static func _data_uri(path: String) -> String:
	var tex := load(path) as Texture2D
	if tex == null:
		return ""
	return "data:image/png;base64," + Marshalls.raw_to_base64(tex.get_image().save_png_to_buffer())


## JS, который перерисовывает страницу. Строится один раз (картинки — внутри, base64).
static func script() -> String:
	if _js == "":
		_js = JS.replace("__LOGO__", _data_uri(LOGO)).replace("__NAV__", _data_uri(NAV))
	return _js


const JS := r"""(function(){
if (window.__g2011) return; window.__g2011 = 1;
var L = location, P = new URLSearchParams(L.search);
var q = P.get('q') || '';
var home = (L.pathname == '/' || L.pathname == '/webhp') && !q;
var serp = L.pathname == '/search' && q && !P.get('tbm') && !P.get('udm');
if (!home && !serp) return;
var LOGO = '__LOGO__', NAV = '__NAV__';
function esc(s){ return String(s).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
function enc(s){ return encodeURIComponent(s); }

var res = [], stats = '';
if (serp) {
	var seen = {};
	document.querySelectorAll('#rso a h3, #search a h3').forEach(function(h){
		var a = h.closest('a'); if (!a || !a.href || a.href.indexOf('http') != 0) return;
		if (seen[a.href]) return; seen[a.href] = 1;
		var b = h.closest('.MjjYud') || h.closest('.g') || h.closest('[data-hveid]') || a.parentElement;
		var sn = b && b.querySelector('.VwiC3b, [data-sncf="1"], .ITZIwc, .lEBKkf, [style*="line-clamp"]');
		var ct = b && b.querySelector('cite');
		var d = ct ? ct.innerText.replace(/\s*›\s*/g, '/').replace(/\s+/g, '') : '';
		res.push({t: h.innerText, u: a.href, s: sn ? sn.innerText : '', d: d});
	});
	if (!res.length) return;   // вёрстка Google поменялась — оставить живую страницу
	var st = document.getElementById('result-stats');
	stats = st ? st.innerText : '';
	if (!stats) {
		var hsh = 0; for (var i = 0; i < q.length; i++) hsh = (hsh * 31 + q.charCodeAt(i)) % 1000003;
		var n = Math.round(Math.pow(10, 4 + (hsh % 400) / 100) / 1000) * 1000;
		stats = 'Результатов: примерно ' + String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' ') +
			' (0,' + (12 + hsh % 30) + ' сек.)';
	}
}

var css = 'html{color-scheme:light}body{margin:0;background:#fff;color:#222;font:13px arial,sans-serif}' +
	'a{color:#12c;text-decoration:none}a:hover{text-decoration:underline}' +
	'#gb{height:30px;background:#2d2d2d;white-space:nowrap;position:relative}' +
	'#gb a{display:inline-block;padding:0 8px;line-height:27px;color:#ccc;font-weight:bold;border-top:3px solid #2d2d2d;text-decoration:none}' +
	'#gb a:hover{background:#4c4c4c;border-top-color:#4c4c4c}' +
	'#gb a.on{color:#fff;border-top-color:#dd4b39}' +
	'#gb .r{position:absolute;right:6px;top:0}' +
	'.box{height:27px;border:1px solid #d9d9d9;border-top-color:#c0c0c0;font:16px arial,sans-serif;padding:0 6px;outline:none;box-sizing:border-box;color:#000;background:#fff}' +
	'.box:hover{border-color:#b9b9b9;border-top-color:#a0a0a0}.box:focus{border-color:#4d90fe}' +
	'.gbtn{height:29px;padding:0 8px;margin:0 4px;border:1px solid #dcdcdc;border-radius:2px;background:linear-gradient(#f5f5f5,#f1f1f1);color:#444;font:bold 11px arial,sans-serif}' +
	'.gbtn:hover{border-color:#c6c6c6;color:#222;box-shadow:0 1px 1px rgba(0,0,0,.1)}' +
	'.sbtn{height:29px;width:60px;margin-left:-1px;border:1px solid #3079ed;border-radius:2px;background:linear-gradient(#4d90fe,#4787ed);vertical-align:top;padding:0}' +
	'.sbtn:hover{border-color:#2f5bb7;background:linear-gradient(#4d90fe,#357ae8)}' +
	'#foot{color:#666;font-size:13px}#foot a{margin:0 8px}' +
	'.csb{background:url(' + NAV + ') no-repeat;display:block;height:40px;overflow:hidden;margin:0 auto}';

var bar = '<div id="gb"><a href="#">+Вы</a><a class="on" href="/webhp?hl=ru">Поиск</a>' +
	'<a href="/search?tbm=isch&hl=ru&q=' + enc(q) + '">Картинки</a><a href="https://maps.google.ru/">Карты</a>' +
	'<a href="https://www.youtube.com/">YouTube</a><a href="https://news.google.ru/">Новости</a>' +
	'<a href="https://mail.google.com/">Gmail</a><a href="https://docs.google.com/">Документы</a>' +
	'<a href="https://calendar.google.com/">Календарь</a><a href="#">Ещё &#9662;</a>' +
	'<span class="r"><a href="https://accounts.google.com/">Войти</a></span></div>';
var mag = '<svg width="14" height="14" viewBox="0 0 14 14" style="vertical-align:middle"><circle cx="5.5" cy="5.5" r="4.2" ' +
	'fill="none" stroke="#fff" stroke-width="2"/><path d="M8.6 8.6L13 13" stroke="#fff" stroke-width="2.4"/></svg>';
var html, title;

if (home) {
	title = 'Google';
	html = bar + '<center><div style="height:90px"></div>' +
		'<img src="' + LOGO + '" width="275" height="95" alt="Google" style="margin-bottom:22px">' +
		'<form action="/search" method="get"><input type="hidden" name="hl" value="ru">' +
		'<input class="box" name="q" autocomplete="off" style="width:541px" autofocus>' +
		'<div style="margin-top:18px"><input class="gbtn" type="submit" value="Поиск в Google">' +
		'<input class="gbtn" type="submit" name="btnI" value="Мне повезёт!"></div></form>' +
		'<div style="margin-top:26px;font-size:13px">Google.ru предлагается на: <a href="/webhp?hl=en">English</a></div>' +
		'</center><div id="foot" style="position:fixed;bottom:0;left:0;right:0;text-align:center;padding:10px 0 12px;border-top:1px solid #e5e5e5;background:#f2f2f2">' +
		'<a href="#">Рекламные программы</a><a href="#">Решения для бизнеса</a><a href="#">+Google</a><a href="#">Всё о Google</a>' +
		'<a href="/webhp?hl=en">Google.com in English</a><div style="margin-top:6px;font-size:11px">&copy; 2011 - ' +
		'<a href="#" style="margin:0">Конфиденциальность</a></div></div>';
} else {
	title = q + ' - Поиск в Google';
	var words = q.toLowerCase().split(/\s+/).filter(function(w){ return w.length > 2; });
	function bold(s){
		var e = esc(s);
		words.forEach(function(w){
			var re = new RegExp('(' + esc(w).replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
			e = e.replace(re, '<b>$1</b>');
		});
		return e;
	}
	var items = res.map(function(r){
		var disp = (r.d || r.u).replace(/^https?:\/\//, '').replace(/^www\.google\.[a-z.]+\/(goto|url)\?.*$/, '');
		try { disp = decodeURI(disp); } catch (e) {}
		if (disp.length > 72) disp = disp.slice(0, 70) + '...';
		return '<li style="margin:0 0 20px;list-style:none;max-width:540px">' +
			'<h3 style="margin:0;font-size:16px;font-weight:normal"><a href="' + esc(r.u) + '" style="text-decoration:underline">' + esc(r.t) + '</a></h3>' +
			'<div style="line-height:1.24">' + (r.s ? '<span>' + bold(r.s) + '</span><br>' : '') +
			'<cite style="color:#093;font-style:normal">' + bold(disp) + '</cite>' +
			' <span style="color:#666">-</span> <a href="#" style="color:#4272db;font-size:13px">Сохранённая копия</a>' +
			' <span style="color:#666">-</span> <a href="#" style="color:#4272db;font-size:13px">Похожие</a></div></li>';
	}).join('');
	var cur = Math.floor((parseInt(P.get('start') || '0') || 0) / 10) + 1;
	function pg(n){ return '/search?hl=ru&q=' + enc(q) + (n > 1 ? '&start=' + (n - 1) * 10 : ''); }
	var first = Math.max(1, cur - 5), nav = '<table style="margin:30px auto 20px;border-collapse:collapse;text-align:center"><tr valign="top">';
	nav += cur > 1 ? '<td style="text-align:left"><a href="' + pg(cur - 1) + '"><span class="csb" style="background-position:0 0;width:53px"></span>' +
		'<span style="display:block;margin-left:18px;font-weight:bold">Назад</span></a></td>' :
		'<td><span class="csb" style="background-position:-24px 0;width:28px"></span></td>';
	for (var n = first; n < first + 10; n++) {
		nav += n == cur ? '<td><span class="csb" style="background-position:-53px 0;width:20px"></span><b style="color:#a90a08">' + n + '</b></td>' :
			'<td><a href="' + pg(n) + '"><span class="csb" style="background-position:-74px 0;width:20px"></span>' + n + '</a></td>';
	}
	nav += '<td style="text-align:left"><a href="' + pg(cur + 1) + '"><span class="csb" style="background-position:-96px 0;width:71px;margin:0"></span>' +
		'<span style="display:block;margin-left:53px;font-weight:bold">Следующая</span></a></td></tr></table>';
	var lnav = ['Везде', 'Картинки', 'Карты', 'Видео', 'Новости', 'Покупки', 'Ещё'].map(function(t, i){
		return i == 0 ? '<div style="padding:4px 0 4px 8px;border-left:2px solid #dd4b39;color:#dd4b39;font-weight:bold">' + t + '</div>' :
			'<div style="padding:4px 0 4px 10px"><a href="' + (i == 1 ? '/search?tbm=isch&hl=ru&q=' + enc(q) : '#') + '" style="color:#222">' + t + '</a></div>';
	}).join('');
	html = bar + '<div style="background:#f1f1f1;border-bottom:1px solid #e5e5e5;height:72px;position:relative">' +
		'<a href="/webhp?hl=ru" style="position:absolute;left:14px;top:12px"><span class="csb" style="background-position:0 -41px;width:116px;height:49px;margin:0"></span></a>' +
		'<form action="/search" method="get" style="position:absolute;left:150px;top:21px;margin:0"><input type="hidden" name="hl" value="ru">' +
		'<input class="box" name="q" value="' + esc(q) + '" autocomplete="off" style="width:540px;vertical-align:top">' +
		'<button class="sbtn" type="submit">' + mag + '</button></form></div>' +
		'<div style="padding:9px 0 0 150px;color:#666;font-size:13px;height:28px">' + esc(stats) + '</div>' +
		'<div style="position:relative"><div style="position:absolute;left:4px;top:0;width:120px">' + lnav + '</div>' +
		'<ol style="margin:0;padding:6px 0 0 150px">' + items + '</ol></div>' + nav +
		'<div id="foot" style="text-align:center;padding:14px 0 20px;border-top:1px solid #e5e5e5;background:#f2f2f2">' +
		'<a href="#">Расширенный поиск</a><a href="#">Настройки поиска</a><a href="#">Справка</a><a href="#">Сообщите нам ваше мнение</a><br><br>' +
		'<a href="/webhp?hl=ru">Главная страница Google</a><a href="#">Рекламные программы</a><a href="#">Решения для бизнеса</a>' +
		'<a href="#">Конфиденциальность</a><a href="#">Всё о Google</a></div>';
}
window.stop();
document.open();
document.write('<!DOCTYPE html><html><head><meta charset="utf-8"><title>' + esc(title) + '</title><style>' + css + '</style></head><body>' + html + '</body></html>');
document.close();
var bx = document.querySelector('.box'); if (bx && home) bx.focus();
})();"""
