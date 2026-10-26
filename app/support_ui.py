"""Assignment 3: recoverable states and local, explicitly exported feedback."""
import json
import streamlit as st

UI_VERSION = '3.1'


def load_screen(loader, model_path, result_path, opening_notice=None):
    try:
        with st.spinner('正在准备分析……'):
            return loader(model_path, result_path)
    except Exception:
        if opening_notice is not None: opening_notice.empty()
        st.title('暂时无法准备分析')
        st.error('所需文件暂时无法读取，填写内容已保留。')
        st.write('请稍后重新加载；仍无法打开时，请联系项目作者。')
        if st.button('重新加载', key='retry_load'):
            st.cache_resource.clear()
            st.rerun()
        st.caption('仍无法打开时，请将此页面截图交给项目作者。不要提交个人填写信息。')
        st.stop()


def feedback_panel(cur):
    with st.expander('反馈：这份结果说明清楚吗？'):
        st.caption('反馈在云端当前会话中暂存，不会自动发送给项目作者。可导出后自行提交，请勿填写个人信息。')
        with st.form('result_feedback', clear_on_submit=False):
            answer = st.radio('你对结果解释的感受', ['清楚','部分不清楚','看不懂'], index=None, key='feedback_choice')
            note = st.text_area('哪里不理解，或希望怎样改？（选填）', max_chars=500, key='feedback_note')
            saved = st.form_submit_button('保存本次反馈')
        if saved:
            if answer is None:
                st.warning('请先选择一项感受，再保存反馈。')
            else:
                st.session_state['feedback_record'] = {
                    'ui_version': UI_VERSION, 'model_version': '2.0',
                    'submission_kind': '演示示例' if cur.get('is_example') else '本次填写',
                    'clarity': answer, 'comment': note.strip(),
                }
        record = st.session_state.get('feedback_record')
        if record:
            st.success('反馈已保存在本次会话中，尚未发送给任何人。')
            st.write('已保存：'+record['clarity'])
            if record['comment']: st.write(record['comment'])
            st.download_button('导出反馈文件', json.dumps(record,ensure_ascii=False,indent=2),
                               file_name='界面反馈_v3.1.json',mime='application/json')
            def discard():
                for k in ['feedback_record','feedback_choice','feedback_note']:
                    st.session_state.pop(k,None)
            st.button('删除本次反馈',key='delete_feedback',on_click=discard)
