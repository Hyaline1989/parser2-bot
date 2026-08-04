function setRowEditing(row, isEditing) {
    row.querySelectorAll('[data-display]').forEach((item) => {
        item.hidden = isEditing;
    });
    row.querySelectorAll('.edit-input').forEach((item) => {
        item.hidden = !isEditing;
    });
    row.querySelector('[data-action="edit"]').hidden = isEditing;
    row.querySelector('[data-action="save"]').hidden = !isEditing;
    row.querySelector('[data-action="cancel"]').hidden = !isEditing;
}

function rememberOriginalValues(row) {
    row.dataset.originalValues = JSON.stringify(
        Array.from(row.querySelectorAll('.edit-input')).map((input) => input.value)
    );
}

function restoreOriginalValues(row) {
    const values = JSON.parse(row.dataset.originalValues || '[]');
    row.querySelectorAll('.edit-input').forEach((input, index) => {
        if (values[index] !== undefined) {
            input.value = values[index];
        }
    });
}

function saveRow(row) {
    const displays = row.querySelectorAll('[data-display]');
    const inputs = row.querySelectorAll('.edit-input');

    inputs.forEach((input, index) => {
        if (input.hasAttribute('data-number')) {
            const value = Math.max(0, Number.parseInt(input.value || '0', 10));
            input.value = String(value);
            displays[index].textContent = value;
        } else {
            displays[index].textContent = input.value.trim() || 'не указана';
        }
    });

    const total = Array.from(row.querySelectorAll('[data-number]')).reduce((sum, input) => {
        return sum + Math.max(0, Number.parseInt(input.value || '0', 10));
    }, 0);
    row.querySelector('[data-total]').textContent = total;
    setRowEditing(row, false);
}

document.querySelectorAll('[data-editable-row]').forEach((row) => {
    row.querySelector('[data-action="edit"]').addEventListener('click', () => {
        rememberOriginalValues(row);
        setRowEditing(row, true);
    });

    row.querySelector('[data-action="save"]').addEventListener('click', () => {
        saveRow(row);
    });

    row.querySelector('[data-action="cancel"]').addEventListener('click', () => {
        restoreOriginalValues(row);
        setRowEditing(row, false);
    });
});

function getNumberValue(input) {
    return Math.max(0, Number.parseInt(input.value || '0', 10));
}

function getDraftReference(draft) {
    return {
        index: Number.parseInt(draft.dataset.draftIndex, 10),
        draft_index: Number.parseInt(draft.dataset.draftIndex, 10),
        message_key: draft.dataset.draftKey || '',
    };
}

async function fetchJsonOrThrow(url, options, fallbackMessage) {
    const response = await fetch(url, options);
    const contentType = response.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) {
        throw new Error('Сервер вернул страницу вместо ответа программы. Проверь, что на сервер загружены app.py и vector_integration.py, потом перезапусти parser2-web.');
    }

    const result = await response.json();
    if (!response.ok || !result.ok) {
        throw new Error(result.message || fallbackMessage);
    }
    return result;
}

function collectVectorRows() {
    return Array.from(document.querySelectorAll('[data-editable-row]')).map((row) => {
        if (!row.querySelector('[data-action="save"]').hidden) {
            saveRow(row);
        }

        const numberInputs = row.querySelectorAll('[data-number]');
        return {
            object: row.children[0].textContent.trim(),
            position: row.querySelector('[data-field="position"]').value.trim(),
            rf_rb_m: getNumberValue(numberInputs[0]),
            rf_rb_f: getNumberValue(numberInputs[1]),
            rf_rb_family: getNumberValue(numberInputs[2]),
            cis_m: getNumberValue(numberInputs[3]),
            cis_f: getNumberValue(numberInputs[4]),
            cis_family: getNumberValue(numberInputs[5]),
            total: Number.parseInt(row.querySelector('[data-total]').textContent || '0', 10),
        };
    });
}

const saveDraftButton = document.querySelector('#save-draft-button');
const saveDraftStatus = document.querySelector('#save-draft-status');

if (saveDraftButton) {
    saveDraftButton.addEventListener('click', async () => {
        const rows = collectVectorRows();
        saveDraftButton.disabled = true;
        saveDraftStatus.textContent = 'Сохраняю...';

        try {
            const response = await fetch('/save-draft', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    source: 'Черновик из Parser2.0',
                    object: document.querySelector('.draft-actions')?.dataset.selectedObject || '',
                    message_key: document.querySelector('.draft-actions')?.dataset.messageKey || '',
                    rows,
                }),
            });
            const result = await response.json();
            saveDraftStatus.textContent = result.message || 'Черновик сохранён';
        } catch (error) {
            saveDraftStatus.textContent = 'Не удалось сохранить черновик';
        } finally {
            saveDraftButton.disabled = false;
        }
    });
}

document.querySelectorAll('[data-action="confirm-draft"]').forEach((button) => {
    button.addEventListener('click', async () => {
        const draft = button.closest('[data-saved-draft]');
        const status = draft.querySelector('[data-draft-status]');
        const index = Number.parseInt(draft.dataset.draftIndex, 10);

        button.disabled = true;
        button.textContent = 'Подтверждаю...';

        try {
            const response = await fetch('/confirm-draft', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(getDraftReference(draft)),
            });
            const result = await response.json();
            if (!response.ok || !result.ok) {
                throw new Error(result.message || 'Не удалось подтвердить');
            }
            updateDraftActionsAfterStatus(button, 'подтверждён');
        } catch (error) {
            button.disabled = false;
            button.textContent = 'Подтвердить';
            alert(error.message);
        }
    });
});


function updateDraftActionsAfterStatus(button, newStatusText) {
    const draft = button.closest('[data-saved-draft]');
    const status = draft.querySelector('[data-draft-status]');
    const actions = button.closest('.saved-actions');
    const deleteButton = actions.querySelector('[data-action="delete-draft"]');
    status.textContent = newStatusText;
    actions.textContent = newStatusText === 'отклонён' ? 'Отклонён' : 'Подтверждён';
    if (newStatusText === 'подтверждён') {
        const previewButton = document.createElement('button');
        previewButton.className = 'small-button vector-preview-button';
        previewButton.type = 'button';
        previewButton.dataset.action = 'vector-preview-draft';
        previewButton.textContent = 'Проверить публикацию в Вектор';
        actions.append(' ');
        actions.append(previewButton);

        const publishButton = document.createElement('button');
        publishButton.className = 'small-button vector-publish-button';
        publishButton.type = 'button';
        publishButton.dataset.action = 'publish-draft-to-vector';
        publishButton.textContent = 'Опубликовать в Вектор';
        publishButton.hidden = true;
        actions.append(' ');
        actions.append(publishButton);
    }
    if (deleteButton) {
        actions.append(' ');
        actions.append(deleteButton);
    }
}

function setSavedRowEditing(row, isEditing) {
    row.querySelectorAll('[data-display]').forEach((item) => {
        item.hidden = isEditing;
    });
    row.querySelectorAll('.edit-input').forEach((item) => {
        item.hidden = !isEditing;
    });
    row.querySelector('[data-action="edit-saved-row"]').hidden = isEditing;
    row.querySelector('[data-action="save-saved-row"]').hidden = !isEditing;
    row.querySelector('[data-action="cancel-saved-row"]').hidden = !isEditing;
}

function rememberSavedRowValues(row) {
    row.dataset.originalValues = JSON.stringify(
        Array.from(row.querySelectorAll('.edit-input')).map((input) => input.value)
    );
}

function restoreSavedRowValues(row) {
    const values = JSON.parse(row.dataset.originalValues || '[]');
    row.querySelectorAll('.edit-input').forEach((input, index) => {
        if (values[index] !== undefined) {
            input.value = values[index];
        }
    });
}

function collectSavedRow(row) {
    const numberInputs = row.querySelectorAll('[data-number]');
    const rowData = {
        object: row.querySelector('[data-saved-object]').textContent.trim(),
        position: row.querySelector('[data-field="position"]').value.trim(),
        rf_rb_m: getNumberValue(numberInputs[0]),
        rf_rb_f: getNumberValue(numberInputs[1]),
        rf_rb_family: getNumberValue(numberInputs[2]),
        cis_m: getNumberValue(numberInputs[3]),
        cis_f: getNumberValue(numberInputs[4]),
        cis_family: getNumberValue(numberInputs[5]),
    };
    rowData.total = rowData.rf_rb_m + rowData.rf_rb_f + rowData.rf_rb_family + rowData.cis_m + rowData.cis_f + rowData.cis_family;
    return rowData;
}

function refreshSavedRowDisplay(row, rowData) {
    const displays = row.querySelectorAll('[data-display]');
    displays[0].textContent = rowData.position;
    displays[1].textContent = rowData.rf_rb_m;
    displays[2].textContent = rowData.rf_rb_f;
    displays[3].textContent = rowData.rf_rb_family;
    displays[4].textContent = rowData.cis_m;
    displays[5].textContent = rowData.cis_f;
    displays[6].textContent = rowData.cis_family;
    row.querySelector('[data-total]').textContent = rowData.total;
}

document.querySelectorAll('[data-saved-row]').forEach((row) => {
    const editButton = row.querySelector('[data-action="edit-saved-row"]');
    const saveButton = row.querySelector('[data-action="save-saved-row"]');
    const cancelButton = row.querySelector('[data-action="cancel-saved-row"]');

    if (!editButton || !saveButton || !cancelButton) {
        return;
    }

    editButton.addEventListener('click', () => {
        rememberSavedRowValues(row);
        setSavedRowEditing(row, true);
    });

    cancelButton.addEventListener('click', () => {
        restoreSavedRowValues(row);
        setSavedRowEditing(row, false);
    });

    saveButton.addEventListener('click', async () => {
        const draft = row.closest('[data-saved-draft]');
        const rowData = collectSavedRow(row);
        saveButton.disabled = true;
        saveButton.textContent = 'Сохраняю...';

        try {
            const response = await fetch('/update-saved-row', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ...getDraftReference(draft),
                    row_index: Number.parseInt(row.dataset.rowIndex, 10),
                    row: rowData,
                }),
            });
            const result = await response.json();
            if (!response.ok || !result.ok) {
                throw new Error(result.message || 'Не удалось сохранить строку');
            }
            refreshSavedRowDisplay(row, result.row);
            draft.querySelector('[data-draft-status]').textContent = 'черновик';
            setSavedRowEditing(row, false);
        } catch (error) {
            alert(error.message);
        } finally {
            saveButton.disabled = false;
            saveButton.textContent = 'Сохранить';
        }
    });
});

document.querySelectorAll('[data-action="reject-draft"]').forEach((button) => {
    button.addEventListener('click', async () => {
        const draft = button.closest('[data-saved-draft]');
        const index = Number.parseInt(draft.dataset.draftIndex, 10);

        button.disabled = true;
        button.textContent = 'Отклоняю...';

        try {
            const response = await fetch('/reject-draft', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(getDraftReference(draft)),
            });
            const result = await response.json();
            if (!response.ok || !result.ok) {
                throw new Error(result.message || 'Не удалось отклонить');
            }
            updateDraftActionsAfterStatus(button, 'отклонён');
        } catch (error) {
            button.disabled = false;
            button.textContent = 'Отклонить';
            alert(error.message);
        }
    });
});

document.addEventListener('click', async (event) => {
    const bulkPreviewButton = event.target.closest('[data-action="vector-preview-confirmed"]');
    if (bulkPreviewButton) {
        const previewBox = document.querySelector('[data-bulk-vector-preview]');
        const publishButton = document.querySelector('[data-action="publish-confirmed-to-vector"]');
        bulkPreviewButton.disabled = true;
        bulkPreviewButton.textContent = 'Проверяю готовые...';
        previewBox.hidden = false;
        previewBox.textContent = 'Проверяю все подтверждённые черновики...';

        try {
            const result = await fetchJsonOrThrow('/vector-preview-confirmed', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
            }, 'Не удалось проверить готовые черновики');
            previewBox.textContent = `Черновиков: ${result.draft_count}\n\n${formatVectorPreview(result.preview)}`;
            publishButton.disabled = result.preview.errors.length > 0;
            publishButton.title = result.preview.errors.length > 0
                ? 'Сначала исправьте ошибки общей проверки'
                : `Опубликовать подтверждённые черновики: ${result.draft_count}`;
        } catch (error) {
            previewBox.textContent = error.message;
            if (publishButton) {
                publishButton.disabled = true;
                publishButton.title = 'Общая проверка завершилась с ошибкой';
            }
        } finally {
            bulkPreviewButton.disabled = false;
            bulkPreviewButton.textContent = 'Проверить всё перед публикацией';
        }
        return;
    }

    const bulkPublishButton = event.target.closest('[data-action="publish-confirmed-to-vector"]');
    if (bulkPublishButton) {
        const previewBox = document.querySelector('[data-bulk-vector-preview]');
        const confirmed = window.confirm('Опубликовать все подтверждённые черновики в Вектор? Перед изменением будет создана резервная копия.');
        if (!confirmed) {
            return;
        }

        bulkPublishButton.disabled = true;
        bulkPublishButton.textContent = 'Публикую всё...';
        previewBox.hidden = false;
        previewBox.textContent = 'Создаю резервную копию и публикую в Вектор...';

        try {
            const result = await fetchJsonOrThrow('/publish-confirmed-to-vector', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
            }, 'Не удалось опубликовать готовые черновики');
            previewBox.textContent = `${result.message}\n\n${formatVectorPreview(result.preview, true)}`;
            window.alert(result.message);
            window.location.reload();
        } catch (error) {
            previewBox.textContent = error.message;
            bulkPublishButton.disabled = false;
            bulkPublishButton.textContent = 'Опубликовать всё в Вектор';
        }
        return;
    }

    const vectorPreviewButton = event.target.closest('[data-action="vector-preview-draft"]');
    if (vectorPreviewButton) {
        event.preventDefault();
        event.stopPropagation();

        const draft = vectorPreviewButton.closest('[data-saved-draft]');
        const previewBox = draft.querySelector('[data-vector-preview]');
        const index = Number.parseInt(draft.dataset.draftIndex, 10);

        vectorPreviewButton.disabled = true;
        vectorPreviewButton.textContent = 'Проверяю...';
        previewBox.hidden = false;
        previewBox.textContent = 'Проверяю, как черновик ляжет в Вектор...';

        try {
            const result = await fetchJsonOrThrow('/vector-preview-draft', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(getDraftReference(draft)),
            }, 'Не удалось проверить публикацию');

            previewBox.textContent = formatVectorPreview(result.preview);
            const publishButton = draft.querySelector('[data-action="publish-draft-to-vector"]');
            if (publishButton) {
                publishButton.hidden = result.preview.errors.length > 0;
            }
        } catch (error) {
            previewBox.textContent = error.message;
        } finally {
            vectorPreviewButton.disabled = false;
            vectorPreviewButton.textContent = 'Проверить публикацию в Вектор';
        }
        return;
    }

    const vectorPublishButton = event.target.closest('[data-action="publish-draft-to-vector"]');
    if (vectorPublishButton) {
        event.preventDefault();
        event.stopPropagation();

        const draft = vectorPublishButton.closest('[data-saved-draft]');
        const previewBox = draft.querySelector('[data-vector-preview]');
        const index = Number.parseInt(draft.dataset.draftIndex, 10);
        const confirmed = window.confirm('Опубликовать этот черновик в Вектор? Цифры в Векторе будут изменены.');
        if (!confirmed) {
            return;
        }

        vectorPublishButton.disabled = true;
        vectorPublishButton.textContent = 'Публикую...';
        previewBox.hidden = false;
        previewBox.textContent = 'Публикую в Вектор...';

        try {
            const result = await fetchJsonOrThrow('/publish-draft-to-vector', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(getDraftReference(draft)),
            }, 'Не удалось опубликовать в Вектор');

            previewBox.textContent = `${result.message}\n\n${formatVectorPreview(result.preview, true)}`;
            updateDraftActionsAfterPublish(vectorPublishButton, result.published_at);
        } catch (error) {
            previewBox.textContent = error.message;
            vectorPublishButton.disabled = false;
            vectorPublishButton.textContent = 'Опубликовать в Вектор';
        }
        return;
    }

    const clearWorkingDraftsButton = event.target.closest('[data-action="delete-working-drafts"]');
    if (clearWorkingDraftsButton) {
        const confirmed = window.confirm('Удалить все черновики и записи “требует проверки”? Подтверждённые записи останутся.');
        if (!confirmed) {
            return;
        }

        clearWorkingDraftsButton.disabled = true;
        clearWorkingDraftsButton.textContent = 'Удаляю...';

        try {
            const response = await fetch('/delete-working-drafts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            const result = await response.json();
            if (!response.ok || !result.ok) {
                throw new Error(result.message || 'Не удалось удалить черновики');
            }
            window.location.reload();
        } catch (error) {
            clearWorkingDraftsButton.disabled = false;
            clearWorkingDraftsButton.textContent = 'Удалить черновики и требует проверки';
            alert(error.message);
        }
        return;
    }

    const deletePublishedDraftsButton = event.target.closest('[data-action="delete-published-drafts"]');
    if (deletePublishedDraftsButton) {
        const confirmed = window.confirm(
            'Удалить все опубликованные черновики из Parser2.0? Цифры в Векторе, история публикаций и резервные копии останутся.'
        );
        if (!confirmed) {
            return;
        }

        deletePublishedDraftsButton.disabled = true;
        deletePublishedDraftsButton.textContent = 'Удаляю опубликованное...';

        try {
            const result = await fetchJsonOrThrow('/delete-published-drafts', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
            }, 'Не удалось удалить опубликованные черновики');
            window.alert(result.message);
            window.location.reload();
        } catch (error) {
            deletePublishedDraftsButton.disabled = false;
            deletePublishedDraftsButton.textContent = 'Удалить опубликованное';
            alert(error.message);
        }
        return;
    }

    const rowDeleteButton = event.target.closest('[data-action="delete-saved-row"]');
    if (rowDeleteButton) {
        const row = rowDeleteButton.closest('[data-saved-row]');
        const draft = rowDeleteButton.closest('[data-saved-draft]');
        const tableBody = row.closest('tbody');
        const confirmed = window.confirm('Удалить эту строку из черновика?');
        if (!confirmed) {
            return;
        }

        rowDeleteButton.disabled = true;
        rowDeleteButton.textContent = 'Удаляю...';

        try {
            const response = await fetch('/delete-saved-row', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ...getDraftReference(draft),
                    row_index: Number.parseInt(row.dataset.rowIndex, 10),
                }),
            });
            const result = await response.json();
            if (!response.ok || !result.ok) {
                throw new Error(result.message || 'Не удалось удалить строку');
            }

            if (result.draft_removed) {
                draft.remove();
                return;
            }

            row.remove();
            tableBody.querySelectorAll('[data-saved-row]').forEach((savedRow, index) => {
                savedRow.dataset.rowIndex = String(index);
            });
            const rowCount = draft.querySelectorAll('[data-saved-row]').length;
            const rowCountLabel = draft.querySelector('summary strong');
            if (rowCountLabel) {
                rowCountLabel.textContent = `${rowCount} строк`;
            }
        } catch (error) {
            rowDeleteButton.disabled = false;
            rowDeleteButton.textContent = 'Удалить';
            alert(error.message);
        }
        return;
    }

    const button = event.target.closest('[data-action="delete-draft"]');
    if (!button) {
        return;
    }

    const draft = button.closest('[data-saved-draft]');
    const index = Number.parseInt(draft.dataset.draftIndex, 10);
    const confirmed = window.confirm('Удалить черновик целиком?');
    if (!confirmed) {
        return;
    }

    button.disabled = true;
    button.textContent = 'Удаляю...';

    try {
        const response = await fetch('/delete-draft', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(getDraftReference(draft)),
        });
        const result = await response.json();
        if (!response.ok || !result.ok) {
            throw new Error(result.message || 'Не удалось удалить черновик');
        }
        draft.remove();
    } catch (error) {
        button.disabled = false;
        button.textContent = 'Удалить черновик';
        alert(error.message);
    }
});

function updateDraftActionsAfterPublish(button, publishedAt) {
    const draft = button.closest('[data-saved-draft]');
    const status = draft.querySelector('[data-draft-status]');
    const actions = button.closest('.saved-actions');
    const deleteButton = actions.querySelector('[data-action="delete-draft"]');
    status.textContent = 'опубликовано';
    actions.textContent = `Опубликовано ${publishedAt}`;
    if (deleteButton) {
        actions.append(' ');
        actions.append(deleteButton);
    }
}

function formatVectorPreview(preview, published = false) {
    const lines = [published ? 'Изменения записаны в Вектор.' : 'Проверка Вектора: запись пока не выполняется.'];

    if (preview.errors.length) {
        lines.push('', 'Нужно исправить:');
        preview.errors.forEach((error) => lines.push(`- ${error}`));
    }

    if (preview.changes.length) {
        lines.push('', 'Будет изменено:');
        preview.changes.forEach((change) => {
            lines.push(
                `- ${change.object} / ${change.position} / ${change.field}: ${change.current} -> ${change.new} (${change.operation})`
            );
        });
    } else if (!preview.errors.length) {
        lines.push('', 'Изменений нет: в Векторе уже такие же цифры.');
    }

    return lines.join('\n');
}

