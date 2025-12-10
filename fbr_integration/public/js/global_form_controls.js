// ================================
// GLOBAL FORM KEYBOARD SHORTCUTS
// ================================

frappe.ui.form.on('*', {
    onload: function(frm) {
        // Prevent multiple bindings
        if (!frm.__alt_tab_bound) {
            frm.__alt_tab_bound = true;

            $(document).on('keydown.fbr_global_nav', function(e) {
                if (e.altKey && e.code === 'PageUp') {
                    e.preventDefault();
                    navigate_to_tab('previous');
                }
                else if (e.altKey && e.code === 'PageDown') {
                    e.preventDefault();
                    navigate_to_tab('next');
                }
            });
        }
    },

    refresh: function(frm) {
        // Hide sidebar by default
        frm.page.sidebar.addClass('hidden');

        // Prevent duplicate buttons
        if (!frm.page.inner_toolbar.find('.btn-fbr-sidebar').length) {
            frm.page.add_inner_button(__('SBar'), function() {
                frm.page.sidebar.toggleClass('hidden');
            }).addClass('btn-fbr-sidebar');
        }
    }
});


function navigate_to_tab(direction) {
    let current_tab = $('.nav-link.active');
    let tabs = $('.nav-link');
    let current_index = tabs.index(current_tab);

    let target_index = null;

    if (direction === 'next') {
        target_index = current_index + 1 < tabs.length ? current_index + 1 : 0;
    }
    else if (direction === 'previous') {
        target_index = current_index - 1 >= 0 ? current_index - 1 : tabs.length - 1;
    }

    if (target_index !== null) {
        let target_tab = $(tabs[target_index]);
        target_tab.tab('show');
    }
}
