webpackJsonp([0],{"4N7q":function(e,n,t){"use strict";Object.defineProperty(n,"__esModule",{value:!0});var r=t("in4f"),a=(t.n(r),$("#gradebook-container")),o=$("#gradebook"),i=$(".marks-sheet-csv-link"),c=$(".gradebook__controls"),s={launch:function(){s.restoreStates(),s.downloadCSVButton(),s.finalGradeSelect(),s.assignmentGradeInputValidator(),s.assignmentGradeInputIncrementByArrows(),s.scrollButtons()},restoreStates:function(){var e=document.querySelectorAll("#gradebook .__input");Array.prototype.forEach.call(e,function(e){if(e.value!==e.defaultValue){var n=e.classList;n.contains("__unsaved")||n.add("__unsaved")}})},downloadCSVButton:function(){i.click(function(){if(o.find(".__unsaved").length>0)return swal({title:"",text:"Сперва сохраните форму,\nчтобы скачать актуальные данные.",type:"warning",confirmButtonText:"Хорошо"}),!1})},finalGradeSelect:function(){o.find("select").each(function(){this.defaultValue=$(this).find("option").filter(function(){return $(this).prop("defaultSelected")}).val()}),o.on("change","select",function(e){s.toggleState(e.target)})},assignmentGradeInputValidator:function(){o.on("keypress","input.__assignment",s.validateNumber),o.on("change","input.__assignment",function(e){var n=parseInt(this.value,10);if($.isNumeric(this.value)&&Number.isInteger(n)){var t=parseInt($(this).attr("max"));n<0?this.value=0:n>t&&(this.value=t)}else this.value="";s.toggleState(e.target)})},validateNumber:function(e){var n=window.event?e.keyCode:e.which;return!(n>31&&(n<48||n>57))},toggleState:function(e){var n=void 0;"input"===e.nodeName.toLowerCase()?n=e:"select"===e.nodeName.toLowerCase()&&(n=e.parentElement);var t=n.classList;e.value!==e.defaultValue?t.add("__unsaved"):t.remove("__unsaved")},assignmentGradeInputIncrementByArrows:function(){o.on("keydown","input.__assignment",function(e){if(38===e.keyCode||40===e.keyCode){var n=this;void 0!==n.increment&&void 0!==n.decrement||(n.increment=$.arrowIncrement.prototype.increment,n.decrement=$.arrowIncrement.prototype.decrement),n.opts={parseFn:function(e){var n=e.match(/^(\D*?)(\d*(,\d{3})*(\.\d+)?)\D*$/);return n&&n[2]?n[1]&&n[1].indexOf("-")>=0?-n[2].replace(",",""):+n[2].replace(",",""):0===e.length?0:NaN}},n.$element=$(this),38===e.keyCode?n.increment():40===e.keyCode&&n.decrement()}})},scrollButtons:function(){a.width()<=o.width()&&(c.on("click",".scroll.left",function(){s.scroll(-1)}),c.on("click",".scroll.right",function(){s.scroll(1)}),c.css("visibility","visible"))},scroll:function(e){var n=100*parseInt(e);if(0!==n){var t=a.scrollLeft();a.scrollLeft(t+n)}}};n.default=s},in4f:function(e,n){!function(e){e.arrowIncrement=function(n,t){var r=this;this.opts=e.extend({},t),this.$element=e(n).keydown(function(e){38===e.keyCode?r.increment():40===e.keyCode&&r.decrement()})},e.arrowIncrement.prototype.increment=function(n){var t,r,a=this.$element.val();t=this.opts.parseFn?this.opts.parseFn(a):e.arrowIncrement.parse(a),isNaN(t)||(r=e.arrowIncrement.compute(t,n,this.opts),this.opts.formatFn&&(r=this.opts.formatFn(r)),this.$element.val(r).change())},e.arrowIncrement.prototype.decrement=function(){this.increment(!0)},e.arrowIncrement.compute=function(n,t,r){var a,o,i=1,c=r&&"number"==typeof r.min,s=r&&"number"==typeof r.max;if(r&&"number"==typeof r.delta&&(i=r.delta),t){if(c&&n<r.min)return n;a=n-i}else{if(s&&n>r.max)return n;a=n+i}return o=Math.max(e.arrowIncrement.decimals(n),e.arrowIncrement.decimals(i)),a=+a.toFixed(o),c&&a<r.min&&(a=r.min),s&&a>r.max&&(a=r.max),a},e.arrowIncrement.decimals=function(e){var n=""+e;return n.indexOf(".")>=0?n.length-1-n.indexOf("."):0},e.arrowIncrement.parse=function(e){var n=e.match(/^(\D*?)(\d*(,\d{3})*(\.\d+)?)\D*$/);return n&&n[2]?n[1]&&n[1].indexOf("-")>=0?-n[2].replace(",",""):+n[2].replace(",",""):NaN},e.fn.arrowIncrement=function(n){return this.each(function(){new e.arrowIncrement(this,n)})}}(jQuery)}});