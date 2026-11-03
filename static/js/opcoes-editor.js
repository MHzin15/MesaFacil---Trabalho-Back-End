'use strict';
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-options-editor]').forEach(editor => {
    const input = document.getElementById(editor.dataset.optionsInput);
    const list = editor.querySelector('[data-option-groups]');
    let groups;
    try { groups = JSON.parse(input.value || '[]'); } catch { groups = []; }
    if (!Array.isArray(groups)) groups = [];
    const id = () => crypto.randomUUID();
    const save = () => { input.value = JSON.stringify(groups); input.dispatchEvent(new Event('input', {bubbles:true})); };
    function button(text, action, label = text) {
      const node = document.createElement('button');
      node.type = 'button'; node.className = 'btn btn-outline-primary';
      node.textContent = text; node.setAttribute('aria-label', label); node.addEventListener('click', action);
      return node;
    }
    function textField(label, value, update, controlId) {
      const wrapper = document.createElement('div');
      wrapper.className = 'option-editor-field';
      const caption = document.createElement('label'); caption.htmlFor = controlId; caption.textContent = label;
      const field = document.createElement('input');
      field.id = controlId; field.className = 'form-control'; field.value = value;
      field.maxLength = 80; field.required = true;
      field.addEventListener('input', () => { update(field.value); save(); });
      wrapper.append(caption, field);
      return wrapper;
    }
    function render(focusId) {
      list.replaceChildren();
      groups.forEach((group, index) => {
        const box = document.createElement('fieldset'); box.className = 'option-editor-group';
        const legend = document.createElement('legend'); legend.textContent = `Grupo ${index + 1}`;
        box.append(legend, textField('Nome do grupo', group.nome, v => { group.nome = v; }, `group-${group.id}`));
        const check = document.createElement('input'); check.type = 'checkbox'; check.checked = group.obrigatorio;
        check.addEventListener('change', () => { group.obrigatorio = check.checked; save(); });
        const label = document.createElement('label'); label.className = 'g-check';
        label.append(check, document.createTextNode('Escolha obrigatória (uma opção)'));
        box.append(label);
        group.opcoes.forEach((option, number) => {
          const row = document.createElement('div'); row.className = 'option-editor-row';
          row.append(textField(`Opção ${number + 1}`, option.nome, v => { option.nome = v; }, `option-${option.id}`),
            button('Remover', () => { group.opcoes.splice(number, 1); save(); render(`group-${group.id}`); }, `Remover opção ${number + 1} do grupo ${index + 1}`));
          box.append(row);
        });
        const add = button('＋ Opção', () => {
          const option = {id:id(), nome:''}; group.opcoes.push(option); save(); render(`option-${option.id}`);
        });
        add.disabled = group.opcoes.length >= 12;
        box.append(add, button('Remover grupo', () => {
          if (!window.confirm(`Remover o grupo “${group.nome || index + 1}” deste produto? Pedidos já enviados preservam as escolhas.`)) return;
          groups.splice(index, 1); save(); render(); editor.querySelector('[data-add-group]').focus();
        }));
        list.append(box);
      });
      editor.querySelector('[data-add-group]').disabled = groups.length >= 6;
      if (focusId) document.getElementById(focusId)?.focus();
    }
    editor.querySelector('[data-add-group]').addEventListener('click', () => {
      const group = {id:id(), nome:'', obrigatorio:true, opcoes:[{id:id(), nome:''}]};
      groups.push(group); save(); render(`group-${group.id}`);
    });
    render();
  });
});
