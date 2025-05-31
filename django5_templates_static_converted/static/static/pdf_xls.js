CKEDITOR.config.toolbar_Pdf =
[
 	{ name: 'document',		items : [ 'NewPage','DocProps','Preview','Print','-' ] },
 	{ name: 'clipboard',	items : [ 'Cut','Copy','Paste','PasteText','-','Undo','Redo' ] },
 	{ name: 'editing',		items : [ 'Find','Replace','-','SelectAll','-','Scayt' ] },
 	'/',
 	{ name: 'basicstyles',	items : [ 'Bold','Italic','Underline','Strike','Subscript','Superscript','-','RemoveFormat' ] },
 	{ name: 'paragraph',	items : [ 'NumberedList','BulletedList','-','Outdent','Indent','-','Blockquote','-','JustifyLeft','JustifyCenter','JustifyRight','JustifyBlock','-','BidiLtr','BidiRtl' ] },
 	{ name: 'links',		items : [ 'Unlink' ] },
 	{ name: 'insert',		items : [ 'Table','HorizontalRule','SpecialChar','PageBreak' ] },
 	'/',
 	{ name: 'styles',		items : [ 'Styles','Format','Font','FontSize' ] },
 	{ name: 'colors',		items : [ 'TextColor','BGColor' ] },
 	{ name: 'tools',		items : [ ] }
];



function generate_pdf(model, id) {

    var form; var form_url;
    form_url = "/pdf-preview/?model=" + model + "&id=" + id;

    $.get(form_url, function(data) {
        $.fancybox(
            data,
            {
                'onClosed': function() {

                    var instance_name = "id_body_pdf";

                }
            }
        );
    });

}

function generate_pdf_directly(model, id, titles) {
    var form_url;

    if (model == 'InspectionPlan'){
        $("#id_inspection_pdf_model").val(model);
        $("#id_inspection_pdf_ids").val(id);
        $("#id_inspection_pdf_titles").val(titles);
        $("#inspections-form").submit();
    }
    else {
        form_url = "/pdf-generate-directly/?model=" + model + "&ids=" + id + "&titles=" + titles;
        location.href = form_url;
    }
}

function generate_xls(model, ids) {

    var form; var form_url;
    if (model == 'InspectionPlan'){
        var titles = []
        $("#inspections-table").find("thead th").each(function(){
            titles.push($(this).text());
        });
        form_url = "/xls-preview/";
        $.post(form_url, {"model": model, "ids": ids, "titles": titles}, function(data) {
            $.fancybox(data);
        });
    }else {
        form_url = "/xls-preview/?model=" + model + "&ids=" + ids;
        $.get(form_url, function(data) {
            $.fancybox(data);

        });
    }


}


