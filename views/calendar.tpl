% include('inc/page_header.tpl')
        <div class="row calendar">
          <div class="col-md-12 col-sm-12 col-xs-12">
            <div class="x_panel">
              <div class="x_title">
                <h2><span aria-hidden="true" class="glyphicon glyphicon-calendar"></span> {{_('Calendar')}}</h2>
                <ul class="nav navbar-right panel_toolbox">
                  <li>
                    <a class="collapse-link"><i class="fa fa-chevron-up"></i></a>
                  </li>
                  <li class="dropdown">
                    <a aria-expanded="false" class="dropdown-toggle" data-toggle="dropdown" href="javascript:;" role="button"><i class="fa fa-wrench" title="{{_('Options')}}"></i></a>
                    <ul class="dropdown-menu" role="menu">
                      <li>
                        <a href="/api/calendar/ical" target="_blank">{{_('iCal')}}</a>
                      </li>
                      <li>
                        <a href="javascript:;" onclick="menu_click('system_settings.html')">{{_('Settings')}}</a>
                      </li>
                    </ul>
                  </li>
                  <li>
                    <a class="close-link"><i class="fa fa-close" title="{{_('Close')}}"></i></a>
                  </li>
                </ul>
                <div class="clearfix"></div>
              </div>
              <div class="x_content">
                <div class="row jumbotron">
                  <div class="col-md-12 col-sm-12 col-xs-12">
                    <h1>{{_('No calendar available')}}</h1>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <script type="text/javascript">
          $(document).ready(function() {
            $.get('api/system',function(data){
              if (data.external_calendar_url != '' && data.external_calendar_url != null) {
                $('div.x_content').html($('<iframe>').addClass('external_calendar').attr('src',data.external_calendar_url));
              } else {
                var calendar = $('div.x_content').fullCalendar({
                  header: {
                    left: 'prev,next today',
                    center: 'title',
                    right: 'month,agendaWeek,agendaDay,listMonth'
                  },
                  eventRender: function(eventObj, $el) {
                    $el.popover({
                       title: eventObj.title,
                       content: eventObj.description,
                       trigger: 'hover',
                       placement: 'top',
                       container: 'body'
                     });
                  },
                  selectable: true,
                  selectHelper: true,
                  editable: true,
                  events: {
                    url: '/api/calendar/'
                  },
                });
              }
            });
            reload_reload_theme();
          });
        </script>
% include('inc/page_footer.tpl')
